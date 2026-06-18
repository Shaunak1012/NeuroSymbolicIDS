"""Print the feature column order after preprocessing.
Use this to verify feature-group indices before editing behaviour logic.
"""
import os
import pandas as pd
import paths

df = pd.read_csv(os.path.join(paths.PROCESSED, "features_train.csv"))
print(f"{df.shape[1]} feature columns:\n")
for i, col in enumerate(df.columns):
    print(f"{i:2d}: {col}")
