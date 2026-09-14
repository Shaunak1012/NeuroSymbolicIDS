"""
exogenous_predicate.py — build knowledge the model provably does NOT already have.

THE PRINCIPLE BEING TESTED
---------------------------
Every symbolic injection this project tried failed, and a literature scan explains
why. The neuro-symbolic IDS work that reports a genuine gain injects knowledge the
neural model *structurally cannot hold*:

  Grov et al. (2024)  "flows not communicating with web servers cannot be web
                       attacks" -- needs an asset inventory. XSS precision
                       0.088 -> 0.213.
  KnowGraph (CCS'24)  logic over relational structure across entities, plus
                       auxiliary models trained on different objectives.
  Kalutharage et al.  MITRE ATT&CK technique mapping -- an external taxonomy.

Ours did the opposite. All seven behaviour predicates in `behavior.py` are
deterministic functions of the same flow features the CNN already reads --
`HighEntropy` is packet-length standard deviation, `BeaconLike` is a function of
destination port. They re-encode information already in the input, so they can
act only as an inductive bias, never add evidence.

**Hypothesis: symbolic knowledge helps exactly to the extent it lies OUTSIDE the
learned feature basis.** That is the same claim as section 4's, applied to the
symbolic side rather than the novel-class side.

WHAT THIS BUILDS
----------------
Host-role knowledge derived from `meta_*.csv` -- Source IP, Destination IP and
ports. **Source and destination IP are NOT among the 67/68 features** (only
destination port is), and no single flow's feature vector can express a property
of the host across many flows. Four predicates:

  ServesPort(dst, port)    does this destination normally serve this port?
  UnusualPortForHost       this flow's port is not in the host's served profile
  FanOut(src)              how many distinct destinations this source contacts
  PairPersistence(src,dst) how many flows this exact pair exchanges

🔴 PROFILES ARE BUILT FROM **TRAIN ONLY** AND APPLIED TO TEST. Aggregating over
the whole capture would be transductive -- a test flow's score would depend on
the rest of the test set, which is the same defect already disclosed for rank
fusion in section 8. Hosts unseen in training get an explicit `UNKNOWN_HOST`
value rather than a silent default, and the fraction of test flows that hit it is
reported, because that fraction bounds how much this knowledge can do at
deployment.

🔴 WHAT IS DELIBERATELY *NOT* USED: attacker identity. CIC-IDS2017's testbed
documents the attacker subnet, and conditioning on it would be label leakage
dressed as domain knowledge -- precisely the spurious correlation Arp et al. call
P4. Only *role* and *structure* are used, never *which host is the adversary*.

THE EXOGENEITY TEST, WHICH IS THE POINT
----------------------------------------
A predicate is only interesting if the model could not already compute it. So
each one is regressed on the 67 features with gradient boosting: **low R² (or AUC
near 0.5) means genuinely exogenous; high means we have merely re-derived an
existing feature** and any downstream gain would be feature engineering wearing a
logical costume. This check is the premise of the whole experiment and it can
fail.

Run:  python scripts/exogenous_predicate.py
Out:  outputs/metadata/exogenous_predicate.json
      data/processed/paper/exo_{train,val,test}.npy
"""
import os
import sys
import json
from collections import defaultdict, Counter

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                          # noqa: E402
import config                                         # noqa: E402
import features as featmod                            # noqa: E402

WEB_PORTS = {80, 443, 8080, 8443}
MIN_FLOWS_FOR_PROFILE = 5      # a host seen fewer times has no reliable profile
PREDICATES = ["UnusualPortForHost", "ServesWebPort", "FanOutLog",
              "PairPersistenceLog", "UnknownHost"]


def read_meta(P, split):
    p = os.path.join(P, "meta_%s.csv" % split)
    if not os.path.exists(p):
        sys.exit("missing %s -- the split does not carry meta" % p)
    d = pd.read_csv(p, low_memory=False)
    d.columns = [c.strip() for c in d.columns]
    ren = {"Src IP": "Source IP", "Dst IP": "Destination IP",
           "Src Port": "Source Port", "Dst Port": "Destination Port"}
    d = d.rename(columns={k: v for k, v in ren.items() if k in d.columns})
    need = ["Source IP", "Destination IP", "Destination Port"]
    miss = [c for c in need if c not in d.columns]
    if miss:
        sys.exit("meta_%s.csv lacks %s" % (split, miss))
    return d


def build_profiles(meta):
    """Host and pair profiles, from TRAINING flows only."""
    served = defaultdict(Counter)       # dst ip -> ports it receives on
    fanout = defaultdict(set)           # src ip -> distinct dsts
    pair = Counter()                    # (src, dst) -> flow count
    for src, dst, port in zip(meta["Source IP"].astype(str),
                              meta["Destination IP"].astype(str),
                              meta["Destination Port"].fillna(-1).astype(int)):
        served[dst][port] += 1
        fanout[src].add(dst)
        pair[(src, dst)] += 1
    # a port counts as "served" by a host only if seen often enough to be a role
    profile = {h: {p for p, c in ports.items() if c >= MIN_FLOWS_FOR_PROFILE}
               for h, ports in served.items()}
    return profile, {k: len(v) for k, v in fanout.items()}, pair


def apply_profiles(meta, profile, fanout, pair):
    n = len(meta)
    out = np.zeros((n, len(PREDICATES)), dtype=np.float32)
    src = meta["Source IP"].astype(str).values
    dst = meta["Destination IP"].astype(str).values
    prt = meta["Destination Port"].fillna(-1).astype(int).values
    for i in range(n):
        known = dst[i] in profile
        ports = profile.get(dst[i], set())
        out[i, 0] = 0.0 if not known else float(prt[i] not in ports)
        out[i, 1] = float(bool(ports & WEB_PORTS))
        out[i, 2] = np.log1p(fanout.get(src[i], 0))
        out[i, 3] = np.log1p(pair.get((src[i], dst[i]), 0))
        out[i, 4] = float(not known)
    return out


def main():
    cfg = config.get()
    P = os.path.join(paths.PROCESSED, cfg["paths"]["paper_subdir"])
    tfm = cfg["protocol"]["feature_transform"]

    print("=" * 100)
    print("EXOGENOUS PREDICATES - knowledge the 67/68 features cannot express")
    print("=" * 100)

    meta = {sp: read_meta(P, sp) for sp in ("train", "val", "test")}
    for sp, m in meta.items():
        X = np.load(os.path.join(P, "X_%s.npy" % sp), mmap_mode="r")
        if len(m) != X.shape[0]:
            sys.exit("meta_%s has %d rows, X_%s has %d - misaligned"
                     % (sp, len(m), sp, X.shape[0]))
    print("meta aligned with every split")

    profile, fanout, pair = build_profiles(meta["train"])
    print("profiles from TRAIN only: %d hosts with a port profile, "
          "%d sources with fan-out, %d pairs"
          % (len(profile), len(fanout), len(pair)))

    exo = {}
    for sp in ("train", "val", "test"):
        exo[sp] = apply_profiles(meta[sp], profile, fanout, pair)
        np.save(os.path.join(P, "exo_%s.npy" % sp), exo[sp])
    unk = float(exo["test"][:, PREDICATES.index("UnknownHost")].mean())
    print("test flows whose destination was unseen in training: %.1f%%"
          % (100 * unk))
    print("  (this bounds what host-role knowledge can do at deployment)")

    # ---- THE EXOGENEITY TEST ------------------------------------------------
    print("\n" + "-" * 100)
    print("EXOGENEITY - can the 68 features already predict each predicate?")
    print("-" * 100)
    print("low R2 / AUC near 0.5 = genuinely outside the basis; high = we have")
    print("merely re-derived an existing feature")

    from sklearn.ensemble import HistGradientBoostingClassifier as HGBC
    from sklearn.ensemble import HistGradientBoostingRegressor as HGBR
    from sklearn.metrics import roc_auc_score, r2_score

    Xtr = featmod.transform(np.load(os.path.join(P, "X_train.npy")), tfm)
    Xte = featmod.transform(np.load(os.path.join(P, "X_test.npy")), tfm)
    # a subsample keeps this a diagnostic rather than an afternoon
    rng = np.random.RandomState(cfg["seed"])
    itr = rng.choice(len(Xtr), min(200000, len(Xtr)), replace=False)

    # Destination Port IS feature 0, so a port-derived predicate could look
    # derivable for a trivial reason. The ablation separates "the flow's own
    # port gives it away" from "the 67 OTHER features genuinely encode host
    # role", and only the second would be a real finding.
    dport = 0
    cols_nodp = [c for c in range(Xtr.shape[1]) if c != dport]
    print("(ablation: also predicted WITHOUT Destination Port, feature %d)"
          % dport)

    res = {}
    for j, name in enumerate(PREDICATES):
        ytr, yte = exo["train"][itr, j], exo["test"][:, j]
        binary = set(np.unique(exo["train"][:, j]).tolist()) <= {0.0, 1.0}
        if binary and (len(np.unique(ytr)) < 2 or len(np.unique(yte)) < 2):
            res[name] = {"kind": "binary", "status": "degenerate"}
            print("  %-22s degenerate (one class)" % name)
            continue
        row = {"kind": "binary" if binary else "continuous"}
        for tag, cols in (("all_features", None), ("no_dest_port", cols_nodp)):
            A = Xtr[itr] if cols is None else Xtr[itr][:, cols]
            B = Xte if cols is None else Xte[:, cols]
            if binary:
                m = HGBC(max_iter=120, random_state=cfg["seed"]).fit(A, ytr)
                row[tag] = float(roc_auc_score(yte, m.predict_proba(B)[:, 1]))
            else:
                m = HGBR(max_iter=120, random_state=cfg["seed"]).fit(A, ytr)
                row[tag] = float(r2_score(yte, m.predict(B)))
        thr = 0.75 if binary else 0.5
        # exogenous only if it resists prediction WITHOUT the port shortcut
        row["exogenous"] = bool(row["no_dest_port"] < thr)
        row["port_shortcut"] = bool(row["all_features"] >= thr
                                    and row["no_dest_port"] < thr)
        res[name] = row
        unit = "AUC" if binary else "R2 "
        print("  %-22s %s all %.3f | without Dst Port %.3f   %s"
              % (name, unit, row["all_features"], row["no_dest_port"],
                 "EXOGENOUS" if row["exogenous"]
                 else "<- already in the features"))

    n_exo = sum(1 for v in res.values() if v.get("exogenous"))
    print("\n  %d of %d predicates are genuinely outside the feature basis"
          % (n_exo, len(res)))
    if n_exo == 0:
        print("  => THE PREMISE FAILS. Nothing here is exogenous, so any "
              "downstream gain would be feature engineering, not symbolic "
              "knowledge. Do not proceed to the injection arms.")

    out = {"predicates": PREDICATES, "web_ports": sorted(WEB_PORTS),
           "min_flows_for_profile": MIN_FLOWS_FOR_PROFILE,
           "profiles_built_from": "train only (inductive)",
           "n_hosts_profiled": len(profile),
           "test_unknown_host_fraction": unk,
           "exogeneity": res, "n_exogenous": n_exo,
           "premise_holds": bool(n_exo > 0),
           "caveats": [
               "Profiles come from TRAIN only and are applied to test, so this "
               "is inductive - aggregating over the whole capture would be "
               "transductive, the defect already disclosed for rank fusion.",
               "Attacker identity is deliberately NOT used. CIC-IDS2017 "
               "documents the attacker subnet and conditioning on it would be "
               "label leakage dressed as domain knowledge (Arp et al. P4).",
               "The unknown-host fraction bounds what host-role knowledge can "
               "do at deployment: those flows get no profile signal at all.",
               "Exogeneity is tested with gradient boosting on the 68 features; "
               "a stronger predictor might recover more, so these thresholds "
               "are evidence, not proof.",
           ]}
    p = os.path.join(paths.METADATA, "exogenous_predicate.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("\nwrote %s" % p)
    print("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
