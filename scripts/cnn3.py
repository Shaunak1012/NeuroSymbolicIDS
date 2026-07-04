import os

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import numpy as np
import pandas as pd
import pickle
import os
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_class_weight
import tensorflow as tf
from tensorflow.keras import layers, models, callbacks, Input
import tensorflow.keras.backend as K

# =========================
# PATHS (see scripts/paths.py)
# =========================
import paths

tf.random.set_seed(42)
np.random.seed(42)

# =========================
# LOAD
# =========================
print("Loading features...")
X_train_full = pd.read_csv(os.path.join(paths.PROCESSED, "features_train.csv")).values
X_test       = pd.read_csv(os.path.join(paths.PROCESSED, "features_test.csv")).values

y_train_str  = np.load(os.path.join(paths.PROCESSED, "labels_train_multiclass.npy"), allow_pickle=True)
y_test_str   = np.load(os.path.join(paths.PROCESSED, "labels_test_multiclass.npy"),  allow_pickle=True)

# =========================
# LABEL STRATEGY
#
# The test set contains attack families NEVER seen in training:
#   Train attacks: DoS variants, FTP-Patator, SSH-Patator, Heartbleed
#   Test attacks:  Bot, DDoS, PortScan, Infiltration, Web Attacks
#
# A multiclass CNN cannot predict classes it was never trained on.
# This IS the zero-day problem — the model's 0% recall on test
# attacks is the honest baseline that motivates LTN.
#
# SOLUTION: Two parallel label schemes.
#
# Scheme A — MULTICLASS on train-only classes:
#
# Scheme B — BINARY (BENIGN vs ATTACK):
# =========================

# SCHEME A: train-only classes
train_classes     = sorted(set(y_train_str))   # 9 classes
test_attack_types = sorted(set(y_test_str) - set(y_train_str))

print(f"\nTrain classes ({len(train_classes)}):")
for c in train_classes:
    print(f"  {c}")
print(f"\nZero-day attack types in test (unseen during training):")
for c in test_attack_types:
    print(f"  {c}  *** ZERO-DAY")

# Encode train labels with train-only classes
le = LabelEncoder()
le.fit(train_classes)

y_train_enc = le.transform(y_train_str)

# For test: known classes get their index, unknown get -1
def encode_test(labels, le):
    encoded = np.full(len(labels), -1, dtype=int)
    known   = np.isin(labels, le.classes_)
    encoded[known] = le.transform(labels[known])
    return encoded

y_test_enc = encode_test(y_test_str, le)

n_classes = len(train_classes)

with open(os.path.join(paths.MODELS, "label_encoder.pkl"), "wb") as f:
    pickle.dump(le, f)
np.save(os.path.join(paths.METADATA, "class_names.npy"),       np.array(train_classes))
np.save(os.path.join(paths.METADATA, "zero_day_classes.npy"),  np.array(test_attack_types))

# SCHEME B: binary labels
y_train_bin = (y_train_str != 'BENIGN').astype(int)
y_test_bin  = (y_test_str  != 'BENIGN').astype(int)
np.save(os.path.join(paths.PROCESSED, "labels_train_binary.npy"), y_train_bin)
np.save(os.path.join(paths.PROCESSED, "labels_test_binary.npy"),  y_test_bin)

print(f"\nTrain attack ratio (binary): {y_train_bin.mean():.4f}")
print(f"Test  attack ratio (binary): {y_test_bin.mean():.4f}")

# =========================
# TRAIN / VAL SPLIT
# =========================
X_train, X_val, y_train, y_val = train_test_split(
    X_train_full, y_train_enc,
    test_size=0.2,
    random_state=42,
    stratify=y_train_enc
)

# =========================
# SCALING
# =========================
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_val   = scaler.transform(X_val)
X_test  = scaler.transform(X_test)

with open(os.path.join(paths.MODELS, "scaler.pkl"), "wb") as f:
    pickle.dump(scaler, f)

# =========================
# CLASS WEIGHTS
# =========================
classes = np.unique(y_train)
weights = compute_class_weight(class_weight='balanced', classes=classes, y=y_train)
class_weight_dict = dict(zip(classes.astype(int), weights))
print("\nClass weights:")
for idx, w in class_weight_dict.items():
    print(f"  {le.classes_[idx]:<35} {w:.4f}")

# =========================
# RESHAPE
# =========================
n_features = X_train.shape[1]
X_train = X_train.reshape(X_train.shape[0], n_features, 1)
X_val   = X_val.reshape(X_val.shape[0],     n_features, 1)
X_test  = X_test.reshape(X_test.shape[0],   n_features, 1)

# =========================
# FOCAL LOSS — CATEGORICAL
# =========================
def categorical_focal_loss(alpha_weights, gamma=2.0):
    alpha_t   = tf.constant(alpha_weights, dtype=tf.float32)
    n_cls     = len(alpha_weights)

    def loss(y_true, y_pred):
        # Keras passes y_true as (batch, 1); flatten or one_hot broadcasts to garbage.
        y_true_int = tf.reshape(tf.cast(y_true, tf.int32), [-1])
        y_pred     = tf.clip_by_value(y_pred, K.epsilon(), 1.0 - K.epsilon())
        pt         = tf.reduce_sum(y_pred * tf.one_hot(y_true_int, n_cls), axis=-1)
        alpha_s    = tf.gather(alpha_t, y_true_int)
        loss_val   = -alpha_s * tf.pow(1.0 - pt, gamma) * tf.math.log(pt)
        return tf.reduce_mean(loss_val)

    return loss

alpha_arr  = np.array([class_weight_dict.get(i, 1.0) for i in range(n_classes)])
alpha_arr  = alpha_arr / alpha_arr.mean()
alpha_list = alpha_arr.tolist()

# =========================
# MODEL — unchanged architecture
# Output: n_classes softmax (train-only classes)
# =========================
def build_model(n_features, n_classes):
    inp = Input(shape=(n_features, 1), name="input")

    x = layers.Conv1D(32, 3, activation='relu', padding='same', name="conv1")(inp)
    x = layers.BatchNormalization(name="bn1")(x)
    x = layers.MaxPooling1D(2, name="pool1")(x)

    x = layers.Conv1D(64, 3, activation='relu', padding='same', name="conv2")(x)
    x = layers.BatchNormalization(name="bn2")(x)
    x = layers.MaxPooling1D(2, name="pool2")(x)

    x = layers.Conv1D(128, 3, activation='relu', padding='same', name="conv3")(x)
    x = layers.BatchNormalization(name="bn3")(x)
    x = layers.MaxPooling1D(2, name="pool3")(x)

    x = layers.Flatten(name="flatten")(x)

    x = layers.Dense(64, activation='relu',
                     kernel_regularizer=tf.keras.regularizers.l2(1e-4),
                     name="embedding")(x)
    x = layers.Dropout(0.4, name="drop1")(x)

    x = layers.Dense(32, activation='relu',
                     kernel_regularizer=tf.keras.regularizers.l2(1e-4),
                     name="dense2")(x)
    x = layers.Dropout(0.3, name="drop2")(x)

    out = layers.Dense(n_classes, activation='softmax', name="output")(x)
    return models.Model(inputs=inp, outputs=out, name="cnn_ids_multiclass")


model = build_model(n_features, n_classes)

model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=3e-4),
    loss=categorical_focal_loss(alpha_list, gamma=2.0),
    metrics=['accuracy']
)

model.summary()

# =========================
# CALLBACKS
# =========================
cb_early_stop = callbacks.EarlyStopping(
    monitor='val_accuracy', patience=8,
    restore_best_weights=True, mode='max', verbose=1
)
cb_reduce_lr = callbacks.ReduceLROnPlateau(
    monitor='val_accuracy', factor=0.5, patience=3,
    min_lr=1e-6, mode='max', verbose=1
)
cb_checkpoint = callbacks.ModelCheckpoint(
    filepath=os.path.join(paths.MODELS, 'model_multiclass_best.keras'),
    monitor='val_accuracy', save_best_only=True, mode='max', verbose=1
)

# =========================
# TRAIN
# =========================
history = model.fit(
    X_train, y_train,
    epochs=50,
    batch_size=256,
    validation_data=(X_val, y_val),
    class_weight=class_weight_dict,
    callbacks=[cb_early_stop, cb_reduce_lr, cb_checkpoint],
    verbose=1
)

# =========================
# SAVE
# =========================
model.save(os.path.join(paths.MODELS, "model_multiclass.keras"))

np.save(os.path.join(paths.ARRAYS, "X_test.npy"),      X_test)
np.save(os.path.join(paths.ARRAYS, "y_test.npy"),      y_test_enc)    # multiclass (-1 = zero-day)
np.save(os.path.join(paths.ARRAYS, "y_test_bin.npy"),  y_test_bin)    # binary ground truth
np.save(os.path.join(paths.ARRAYS, "y_train.npy"),     y_train)
np.save(os.path.join(paths.ARRAYS, "y_val.npy"),       y_val)

with open(os.path.join(paths.METADATA, "history.pkl"), "wb") as f:
    pickle.dump(history.history, f)

# =========================
# EXTRACT EMBEDDINGS
# =========================
embedding_model = models.Model(
    inputs=model.input,
    outputs=model.get_layer("embedding").output,
    name="embedding_extractor"
)

print("\nExtracting embeddings...")
X_train_emb = embedding_model.predict(X_train, batch_size=512, verbose=1)
X_val_emb   = embedding_model.predict(X_val,   batch_size=512, verbose=1)
X_test_emb  = embedding_model.predict(X_test,  batch_size=512, verbose=1)

np.save(os.path.join(paths.EMBEDDINGS, "X_train_emb.npy"), X_train_emb)
np.save(os.path.join(paths.EMBEDDINGS, "X_val_emb.npy"),   X_val_emb)
np.save(os.path.join(paths.EMBEDDINGS, "X_test_emb.npy"),  X_test_emb)

print("\nTRAINING DONE")
print(f"  Train emb : {X_train_emb.shape}")
print(f"  Val emb   : {X_val_emb.shape}")
print(f"  Test emb  : {X_test_emb.shape}")
print("\nKEY RESULT TO RECORD (your LTN baseline):")
print("  CNN alone cannot predict zero-day attack families.")
print("  Run eval.py to get binary PR-AUC — this is what LTN must beat.")