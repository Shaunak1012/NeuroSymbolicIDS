"""
Shared feature transform (Phase 0.3 A/B: signed-log1p beat raw on the paper split).

Use everywhere features are prepared for a model, controlled by config `feature_transform`:

    import features, config
    Xt = features.transform(X, config.get()["protocol"]["feature_transform"])
"""
import numpy as np


def signed_log1p(X):
    """Robust heavy-tail compressor for signed data: sign(x)*log1p(|x|).
    Handles the -1 sentinels in Init_Win_bytes etc. that plain log1p can't."""
    X = np.asarray(X, dtype=np.float64)
    return np.sign(X) * np.log1p(np.abs(X))


def transform(X, mode="log1p"):
    if mode == "raw":
        return np.asarray(X, dtype=np.float64)
    if mode == "log1p":
        return signed_log1p(X)
    raise ValueError(f"unknown feature_transform: {mode!r}")
