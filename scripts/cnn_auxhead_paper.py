"""
cnn_auxhead_paper.py — Phase 2 (d): representation-level symbolic injection.

Instead of a logic *constraint* fighting the classification loss (LTN/SAT), we add a
second head that PREDICTS the fuzzy behaviours from the shared embedding. This is a
well-behaved auxiliary/multi-task loss — it shapes the representation to be
behaviour-aware without competing with classification, and the resulting embeddings
directly benefit the KG (Phase 4).

  loss = focal(class) + LAMBDA * BCE(behaviour)

Config:  AUX_LAMBDA (default 0.5)  AUX_EPOCHS (default 50)  AUX_SUBSET (default 0)
Eval via metrics.py (zero-day-only headline). Logged to runs.jsonl.
"""
import os
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
import numpy as np
import tensorflow as tf
tf.config.threading.set_intra_op_parallelism_threads(16)
tf.config.threading.set_inter_op_parallelism_threads(2)
from tensorflow.keras import layers, models, callbacks, Input
import tensorflow.keras.backend as K
from sklearn.preprocessing import StandardScaler, LabelEncoder

import paths, config, features, behavior, metrics, tracking

cfg = config.get(); SEED = cfg["seed"]
tf.random.set_seed(SEED); np.random.seed(SEED)
PAPER = os.path.join(paths.PROCESSED, cfg["paths"]["paper_subdir"]); TFM = cfg["protocol"]["feature_transform"]
LAMBDA = float(os.environ.get("AUX_LAMBDA", "0.5"))
EPOCHS = int(os.environ.get("AUX_EPOCHS", "50")); SUBSET = int(os.environ.get("AUX_SUBSET", "0"))
BEH = behavior.BEHAVIOUR_NAMES[:5]   # drop RepeatedConnections (constant 0)

def load(s): return (np.load(os.path.join(PAPER, f"X_{s}.npy")),
                     np.load(os.path.join(PAPER, f"y_{s}_mc.npy"), allow_pickle=True))
Xtr_raw, ytr = load("train"); Xval_raw, yval = load("val"); Xte_raw, yte = load("test")
zero_day = set(np.load(os.path.join(PAPER, "zero_day_classes.npy"), allow_pickle=True).tolist())

# behaviour targets (fuzzy [0,1]); fresh thresholds on paper train
thr = behavior.compute_thresholds(Xtr_raw)
def beh_targets(Xraw):
    b = behavior.abstract_behaviours(Xraw, thr)
    return np.stack([b[n] for n in BEH], axis=1).astype(np.float32)
Btr, Bval = beh_targets(Xtr_raw), beh_targets(Xval_raw)

sc = StandardScaler().fit(features.transform(Xtr_raw, TFM))
def prep(Xraw): return sc.transform(features.transform(Xraw, TFM)).reshape(-1, Xtr_raw.shape[1], 1).astype(np.float32)
Xtr, Xval, Xte = prep(Xtr_raw), prep(Xval_raw), prep(Xte_raw)
le = LabelEncoder().fit(ytr); nc = len(le.classes_); benign_idx = list(le.classes_).index("BENIGN")
ytr_e, yval_e = le.transform(ytr), le.transform(yval)

if SUBSET > 0:
    i = np.random.RandomState(SEED).choice(len(Xtr), min(SUBSET, len(Xtr)), replace=False)
    Xtr, ytr_e, Btr = Xtr[i], ytr_e[i], Btr[i]; print(f"[SMOKE] {len(Xtr)} rows")

def focal(gamma=2.0):
    def loss(yt, yp):
        yt = tf.reshape(tf.cast(yt, tf.int32), [-1]); yp = tf.clip_by_value(yp, K.epsilon(), 1 - K.epsilon())
        pt = tf.reduce_sum(yp * tf.one_hot(yt, nc), axis=-1)
        return tf.reduce_mean(-tf.pow(1 - pt, gamma) * tf.math.log(pt))
    return loss

inp = Input((Xtr.shape[1], 1), name="input"); x = inp
for f, n in [(32, "1"), (64, "2"), (128, "3")]:
    x = layers.Conv1D(f, 3, padding="same", activation="relu", name=f"conv{n}")(x)
    x = layers.BatchNormalization(name=f"bn{n}")(x); x = layers.MaxPooling1D(2, name=f"pool{n}")(x)
x = layers.Flatten(name="flatten")(x)
emb = layers.Dense(64, activation="relu", kernel_regularizer=tf.keras.regularizers.l2(1e-4), name="embedding")(x)
c = layers.Dropout(0.4)(emb); c = layers.Dense(32, activation="relu", name="dense2")(c); c = layers.Dropout(0.3)(c)
class_out = layers.Dense(nc, activation="softmax", name="class_out")(c)
beh_out = layers.Dense(len(BEH), activation="sigmoid", name="beh_out")(emb)   # from shared embedding
model = models.Model(inp, [class_out, beh_out], name="cnn_auxhead")
model.compile(optimizer=tf.keras.optimizers.Adam(3e-4),
              loss={"class_out": focal(), "beh_out": "binary_crossentropy"},
              loss_weights={"class_out": 1.0, "beh_out": LAMBDA},
              metrics={"class_out": "sparse_categorical_accuracy"})

cbs = [callbacks.EarlyStopping(monitor="val_class_out_sparse_categorical_accuracy", patience=8, mode="max", restore_best_weights=True),
       callbacks.ReduceLROnPlateau(monitor="val_class_out_sparse_categorical_accuracy", factor=0.5, patience=3, mode="max", min_lr=1e-6)]
print(f"Training aux-head (lambda={LAMBDA}) ...")
model.fit(Xtr, {"class_out": ytr_e, "beh_out": Btr},
          validation_data=(Xval, {"class_out": yval_e, "beh_out": Bval}),
          epochs=EPOCHS, batch_size=256, callbacks=cbs, verbose=2)

prob = model.predict(Xte, batch_size=1024, verbose=0)[0]
patk = 1.0 - prob[:, benign_idx]
res = metrics.evaluate(yte, patk, zero_day, fpr=0.01); metrics.print_report(res)
TAG = f"cnn_auxhead_l{LAMBDA}"
np.save(os.path.join(paths.PREDICTIONS, f"y_prob_{TAG}_test.npy"), patk.astype(np.float32))
if SUBSET == 0:
    # persist the model — without this the run cannot be re-scored (e.g. in log-odds)
    # without a full retrain. See scripts/rescore_logits.py.
    model.save(os.path.join(paths.MODELS, f"{TAG}.keras"))
    emb_model = models.Model(model.input, model.get_layer("embedding").output)
    for nm, arr in [("train", Xtr), ("test", Xte)]:
        np.save(os.path.join(paths.EMBEDDINGS, f"X_{nm}_{TAG}_emb.npy"), emb_model.predict(arr, batch_size=1024, verbose=0))
    tracking.log_run(TAG, {"protocol": "paper", "lambda": LAMBDA, "seed": SEED}, metrics.flatten(res))
    print(f"logged {TAG}")
print(f"DONE ({TAG})")
