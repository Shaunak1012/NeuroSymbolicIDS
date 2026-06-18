"""
behavior.py — Symbolic behaviour abstraction for NeuroSymbolic-IDS.

Maps raw CIC-IDS2017 flow features into a small set of named, human-meaningful
*behaviours*, each expressed as a fuzzy confidence in [0, 1]. These behaviours are
the shared symbolic vocabulary consumed by:
  - the LTN axioms (behaviour -> class rules that transfer to zero-day attacks), and
  - the Knowledge Graph (behaviour edge weights).

Design notes
------------
* Operates on RAW (unscaled) features — the values in `features_train.csv` /
  `features_test.csv` BEFORE StandardScaler — so thresholds are interpretable
  (e.g. "Flow Packets/s above the 95th percentile"). Do NOT pass scaled data.
* Fully VECTORISED (whole-array numpy) — the previous per-row Python loop was
  unusable on 1.6M flows.
* Thresholds are data-driven percentiles computed on the training set and saved
  to `outputs/metadata/behaviour_thresholds.npy`.
* Outputs are fuzzy [0, 1] confidences, not hard booleans, so they plug directly
  into product fuzzy logic and weighted graph edges.

Feature indices are VERIFIED against the 68-column post-preprocessing order
(run `python scripts/check.py` to re-confirm if preprocessing changes).

Why these behaviours (validated empirically — see __main__):
  - BurstTraffic / HighVolume / LargePackets / HighEntropy catch volume/size-heavy
    attacks (DoS, DDoS) — strongly attack-discriminative on training data.
  - ScanProbe catches short, near-empty probe flows (e.g. the zero-day PortScan),
    which the volume/size behaviours miss. Flag-count based detection was tried and
    DROPPED: in CIC-IDS2017 the flag-count columns are ~0 even for real scans, so
    they carry no signal — flow structure (short duration + tiny payload) does.
  - RepeatedConnections needs source/dest IP+port (dropped by preprocessing) and is
    therefore UNAVAILABLE in v1 — see KNOWN_ISSUES / target docs.
"""

import os
import numpy as np
import paths

# =============================================================
# VERIFIED FEATURE INDICES  (68 columns after preprocess.py)
# Confirm with: python scripts/check.py
# =============================================================
IDX = {
    "flow_duration": 1,
    "tot_fwd_pkts":  2,
    "tot_bwd_pkts":  3,
    "tot_len_fwd":   4,
    "tot_len_bwd":   5,
    "flow_bytes_s":  14,
    "flow_pkts_s":   15,
    "flow_iat_mean": 16,
    "flow_iat_std":  17,
    "fwd_pkts_s":    33,
    "bwd_pkts_s":    34,
    "min_pkt_len":   35,
    "max_pkt_len":   36,
    "pkt_len_mean":  37,
    "pkt_len_std":   38,
    "pkt_len_var":   39,
    "fin": 40, "syn": 41, "rst": 42, "psh": 43, "ack": 44, "urg": 45, "ece": 46,
    "down_up_ratio": 47,
}

BEHAVIOUR_NAMES = [
    "BurstTraffic",        # high packet rate (DoS/DDoS/flood)
    "HighVolume",          # high packet/byte counts
    "LargePackets",        # large average payload (exfil / volumetric)
    "HighEntropy",         # APPROX: high packet-size variance (NOT true Shannon entropy)
    "ScanProbe",           # short, near-empty probe flows (PortScan-like)
    "RepeatedConnections", # UNAVAILABLE without IP/port side table -> always 0.0
]

REPEATED_CONNECTIONS_AVAILABLE = False

# "high-X" ramps: confidence rises as the signal rises. (lo=p50, hi=p95)
_HIGH_SIGNALS = {
    "burst":     "flow_pkts_s",
    "volume":    "_volume",       # tot_fwd_pkts + tot_bwd_pkts
    "large_pkt": "pkt_len_mean",
    "entropy":   "pkt_len_std",
}
# "low-X" ramps: confidence rises as the signal FALLS. (lo=p5, hi=p40)
_LOW_SIGNALS = {
    "scan_dur":     "flow_duration",
    "scan_payload": "_payload",    # tot_len_fwd + tot_len_bwd
}


# -------------------------------------------------------------
# helpers
# -------------------------------------------------------------
def _as_2d(X):
    """Accept (N, F) or (N, F, 1); return a contiguous (N, F) float array."""
    X = np.asarray(X)
    if X.ndim == 3:
        X = X.reshape(X.shape[0], -1)
    return X.astype(np.float64, copy=False)


def _col(X, name):
    return X[:, IDX[name]]


def _signal(X, name):
    """Resolve a ramp signal: a raw column or a derived quantity."""
    if name == "_volume":
        return _col(X, "tot_fwd_pkts") + _col(X, "tot_bwd_pkts")
    if name == "_payload":
        return _col(X, "tot_len_fwd") + _col(X, "tot_len_bwd")
    return _col(X, name)


def _ramp_high(x, lo, hi):
    """Fuzzy membership for 'high X': 0 below lo, 1 above hi, linear between."""
    x = np.asarray(x, dtype=np.float64)
    if hi <= lo:
        return (x > lo).astype(np.float64)
    return np.clip((x - lo) / (hi - lo), 0.0, 1.0)


def _ramp_low(x, lo, hi):
    """Fuzzy membership for 'low X': 1 at/below lo, 0 at/above hi, linear between."""
    x = np.asarray(x, dtype=np.float64)
    if hi <= lo:
        return (x < hi).astype(np.float64)
    return np.clip((hi - x) / (hi - lo), 0.0, 1.0)


# -------------------------------------------------------------
# thresholds
# -------------------------------------------------------------
def compute_thresholds(X_train_raw, high_pct=(50, 95), low_pct=(5, 40)):
    """
    Compute (lo, hi) percentile pairs for each fuzzy ramp from TRAINING data.
    Returns a dict ready to be saved / passed to abstract_behaviours().
    """
    X = _as_2d(X_train_raw)
    thr = {}
    for key, sig in _HIGH_SIGNALS.items():
        s = _signal(X, sig)
        thr[key] = (float(np.percentile(s, high_pct[0])), float(np.percentile(s, high_pct[1])))
    for key, sig in _LOW_SIGNALS.items():
        s = _signal(X, sig)
        thr[key] = (float(np.percentile(s, low_pct[0])), float(np.percentile(s, low_pct[1])))
    return thr


def save_thresholds(thr, path=None):
    if path is None:
        path = os.path.join(paths.METADATA, "behaviour_thresholds.npy")
    np.save(path, thr, allow_pickle=True)
    print(f"[behavior] saved thresholds -> {path}")
    return path


def load_thresholds(path=None):
    """Load saved thresholds, or fall back to neutral defaults with a warning."""
    if path is None:
        path = os.path.join(paths.METADATA, "behaviour_thresholds.npy")
    if os.path.exists(path):
        thr = np.load(path, allow_pickle=True).item()
        print(f"[behavior] loaded thresholds <- {path}")
        return thr
    print("[behavior] WARNING: threshold file not found — using neutral defaults. "
          "Run compute_thresholds() on training data and save_thresholds().")
    neutral = {k: (0.0, 1.0) for k in _HIGH_SIGNALS}
    neutral.update({k: (0.0, 1.0) for k in _LOW_SIGNALS})
    return neutral


# -------------------------------------------------------------
# behaviour extraction (vectorised)
# -------------------------------------------------------------
def abstract_behaviours(X_raw, thresholds=None):
    """
    Map raw flow features -> dict of fuzzy behaviour confidences.

    Parameters
    ----------
    X_raw      : (N, 68) or (N, 68, 1) RAW (unscaled) feature array.
    thresholds : dict from compute_thresholds(); if None, loaded from disk.

    Returns
    -------
    dict[str, np.ndarray]  — each value an (N,) float array in [0, 1].
                             Keys are exactly BEHAVIOUR_NAMES.
    """
    X = _as_2d(X_raw)
    if thresholds is None:
        thresholds = load_thresholds()

    # ScanProbe = short duration AND tiny payload (product fuzzy-AND).
    short_dur   = _ramp_low(_signal(X, "flow_duration"), *thresholds["scan_dur"])
    tiny_payload = _ramp_low(_signal(X, "_payload"),     *thresholds["scan_payload"])

    out = {}
    out["BurstTraffic"]  = _ramp_high(_signal(X, "flow_pkts_s"), *thresholds["burst"])
    out["HighVolume"]    = _ramp_high(_signal(X, "_volume"),     *thresholds["volume"])
    out["LargePackets"]  = _ramp_high(_col(X, "pkt_len_mean"),   *thresholds["large_pkt"])
    out["HighEntropy"]   = _ramp_high(_col(X, "pkt_len_std"),    *thresholds["entropy"])
    out["ScanProbe"]     = short_dur * tiny_payload
    out["RepeatedConnections"] = np.zeros(X.shape[0], dtype=np.float64)  # unavailable
    return out


def behaviour_matrix(X_raw, thresholds=None):
    """Same as abstract_behaviours but returned as (N, len(BEHAVIOUR_NAMES)) array."""
    b = abstract_behaviours(X_raw, thresholds)
    return np.stack([b[name] for name in BEHAVIOUR_NAMES], axis=1)


# -------------------------------------------------------------
# self-test / threshold generator
#   python scripts/behavior.py
# Fits thresholds on features_train.csv, saves them, and validates that
# behaviours fire more on attack flows than benign (discriminativeness check).
# -------------------------------------------------------------
if __name__ == "__main__":
    import pandas as pd

    feat_path = os.path.join(paths.PROCESSED, "features_train.csv")
    lbl_path  = os.path.join(paths.PROCESSED, "labels_train_binary.npy")
    print(f"Loading {feat_path} ...")
    X = pd.read_csv(feat_path).values
    print(f"  shape = {X.shape}")

    thr = compute_thresholds(X)
    save_thresholds(thr)
    print("\nThresholds:")
    for k, (lo, hi) in thr.items():
        print(f"  {k:13s}: lo={lo:.4g}  hi={hi:.4g}")

    beh = abstract_behaviours(X, thr)

    print("\nBehaviour prevalence (mean confidence over all training flows):")
    for name in BEHAVIOUR_NAMES:
        print(f"  {name:20s}: {beh[name].mean():.4f}")

    if os.path.exists(lbl_path):
        y = np.load(lbl_path)
        benign = y == 0
        attack = y == 1
        print(f"\nDiscriminativeness  (benign n={benign.sum():,}  attack n={attack.sum():,})")
        print(f"  {'behaviour':20s} {'benign':>8s} {'attack':>8s} {'ratio':>8s}")
        for name in BEHAVIOUR_NAMES:
            b_mean = beh[name][benign].mean()
            a_mean = beh[name][attack].mean()
            ratio = (a_mean / b_mean) if b_mean > 1e-9 else float("inf")
            print(f"  {name:20s} {b_mean:8.4f} {a_mean:8.4f} {ratio:8.2f}")
        print("\n(ratio > 1 means the behaviour fires more on attacks. Note ScanProbe "
              "mainly targets the zero-day PortScan in the TEST set, so its training "
              "ratio understates its value — validate on test by class.)")
