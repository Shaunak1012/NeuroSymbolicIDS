"""
Central filesystem paths for the NeuroSymbolic-IDS pipeline.

Every pipeline script imports this module so that artifacts are written to and
read from a single, organised directory tree instead of being dumped in the
project root. Output directories are created on import.

Layout
------
data/raw_csv/        input CIC-IDS2017 CSVs            -> RAW_CSV
data/processed/      cleaned data, features, labels    -> PROCESSED
models/              trained models + fitted scalers   -> MODELS
outputs/arrays/      model-ready tensors & label splits-> ARRAYS
outputs/embeddings/  64-dim CNN/LTN embeddings         -> EMBEDDINGS
outputs/predictions/ softmax / P(attack) score arrays  -> PREDICTIONS
outputs/metadata/    class names, history, thresholds  -> METADATA
outputs/figures/     evaluation plots (.png)           -> FIGURES
"""

import os

# Project root = parent of the scripts/ directory that contains this file.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- Inputs ---
RAW_CSV = os.path.join(ROOT, "data", "raw_csv")

# --- Intermediate data ---
PROCESSED = os.path.join(ROOT, "data", "processed")

# --- Models + fitted transformers ---
MODELS = os.path.join(ROOT, "models")

# --- Pipeline outputs ---
ARRAYS      = os.path.join(ROOT, "outputs", "arrays")
EMBEDDINGS  = os.path.join(ROOT, "outputs", "embeddings")
PREDICTIONS = os.path.join(ROOT, "outputs", "predictions")
METADATA    = os.path.join(ROOT, "outputs", "metadata")
FIGURES     = os.path.join(ROOT, "outputs", "figures")

# Create output directories on import (RAW_CSV is an input, not created here).
for _d in (PROCESSED, MODELS, ARRAYS, EMBEDDINGS, PREDICTIONS, METADATA, FIGURES):
    os.makedirs(_d, exist_ok=True)


def p(directory, filename):
    """Convenience: paths.p(paths.MODELS, 'scaler.pkl')."""
    return os.path.join(directory, filename)
