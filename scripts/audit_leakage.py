"""
audit_leakage.py — measure exact-duplicate overlap between the paper split's
train and test sets, per class.

Why this exists
---------------
CIC-IDS2017 contains many duplicate flows and `preprocess.py` deliberately keeps
them ("preserve all flows for realistic evaluation"). The paper-aligned split is
STRATIFIED RANDOM, so identical feature vectors can land on both sides. That is a
documented criticism of this dataset (Engelen et al. 2021) and a reviewer will
check it.

Measured 2026-07-29 (seed-independent — this is a property of the split, not a model):

    train 883,796 rows, 764,508 unique  -> 13.5% internally duplicated
    test  114,658 rows, 106,593 unique  ->  7.0% internally duplicated
    11,848 distinct feature vectors appear in BOTH
    19,513 / 114,658 test rows (17.0%) are exact copies of a training row

    PortScan     58.3%        Bot                        0.0%
    SSH-Patator  48.6%        Heartbleed                 0.0%
    FTP-Patator  29.6%        Infiltration               0.0%
    DoS Hulk     25.3%        Web Attack Brute Force     0.0%
    DoS slowloris 9.1%        Web Attack XSS             0.0%
    BENIGN        6.9%        Web Attack Sql Injection   0.0%

Interpretation
--------------
ZERO-DAY METRICS ARE SAFE. All six zero-day classes measure exactly 0.0% because
they are test-only by construction and therefore cannot overlap train. The macro
zero-day PR-AUC headline is unaffected.

WHAT IS CONTAMINATED is the ~0.98 "overall binary PR-AUC" on known classes, where
PortScan at 58% overlap is substantially a lookup rather than detection. Note the
knock-on: config.yaml's log1p A/B was decided on that overall metric (0.980 vs
0.965), so the feature transform was selected using a contaminated number.

Recommended handling (NOT de-duplication -- that changes the protocol and breaks
comparability with the base paper): report the overall metric as-is AND a
unique-flows-only variant, stating the duplicate rate explicitly.

Run:  python scripts/audit_leakage.py
"""
import hashlib

import numpy as np

import paths


def row_keys(X):
    """MD5 of each row's raw bytes -> exact-feature-vector identity."""
    Xc = np.ascontiguousarray(X)
    return np.array([hashlib.md5(r.tobytes()).hexdigest() for r in Xc])


def main():
    P = paths.PAPER
    Xtr = np.load(f"{P}/X_train.npy")
    Xte = np.load(f"{P}/X_test.npy")
    yte = np.load(f"{P}/y_test_mc.npy", allow_pickle=True)

    print("hashing rows (this takes a minute on ~1M rows) ...")
    ktr, kte = row_keys(Xtr), row_keys(Xte)
    str_, ste = set(ktr), set(kte)
    overlap = str_ & ste

    print(f"\ntrain {len(ktr):,} rows, {len(str_):,} unique "
          f"({1 - len(str_) / len(ktr):.1%} internally duplicated)")
    print(f"test  {len(kte):,} rows, {len(ste):,} unique "
          f"({1 - len(ste) / len(kte):.1%} internally duplicated)")
    print(f"\ndistinct feature vectors in BOTH: {len(overlap):,}")

    leaked = np.isin(kte, list(overlap))
    print(f"TEST rows that are exact copies of a TRAIN row: "
          f"{leaked.sum():,} / {len(kte):,} = {leaked.mean():.1%}\n")

    zd = set(np.load(f"{P}/zero_day_classes.npy", allow_pickle=True).tolist())
    print(f"{'class':30s} {'n':>7s} {'leaked':>8s}")
    print("-" * 49)
    for c in sorted(set(yte)):
        m = yte == c
        tag = "ZD" if c in zd else "  "
        print(f"{tag} {c:27s} {m.sum():7d} {leaked[m].mean():7.1%}")

    zd_mask = np.isin(yte, list(zd))
    print(f"\nzero-day rows leaked: {leaked[zd_mask].sum()} "
          f"(expected 0 — zero-day is test-only by construction)")


if __name__ == "__main__":
    main()
