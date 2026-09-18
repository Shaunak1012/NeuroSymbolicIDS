"""
Leakage-boundary and split-integrity tests for the paper split (audit F-09).

Two kinds of test live here, and the difference matters:

* INVARIANTS must hold. A failure means the pipeline is broken: a zero-day label in
  training, a scaler fitted on more than train, a feature count that changed.
* PINNED MEASUREMENTS record a known defect at its measured size (17.02 % duplicates,
  54.88 % shared 5-tuples, 100 % temporal overlap, 4.11x benign removal). They are
  not claims that the value is acceptable. They exist so that the value cannot
  change without someone noticing -- if a split fix lowers one, update the pin in
  the same commit and say so.

Everything here reads artefacts that are gitignored (data/, models/). Tests skip,
rather than fail, when those are absent, so a fresh clone runs clean.

Run:  python -m unittest discover -s tests -v
"""
import hashlib
import json
import os
import pickle
import sys
import unittest

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import paths      # noqa: E402
import config     # noqa: E402
import features   # noqa: E402

P = paths.PAPER
HAVE_SPLIT = os.path.exists(os.path.join(P, "X_train.npy"))
HAVE_META = os.path.exists(os.path.join(P, "meta_test.csv"))
SCALER = os.path.join(paths.MODELS, "scaler_paper.pkl")
RECORD = os.path.join(paths.METADATA, "split_integrity.json")


def _y(split):
    return np.load(os.path.join(P, "y_%s_mc.npy" % split), allow_pickle=True)


@unittest.skipUnless(HAVE_SPLIT, "paper split arrays not present")
class LabelBoundary(unittest.TestCase):
    """INVARIANT: zero-day families never reach training or validation."""

    def test_no_zero_day_in_train_or_val(self):
        zd = set(config.get()["zero_day_classes"])
        for split in ("train", "val"):
            with self.subTest(split=split):
                self.assertEqual(set(_y(split).tolist()) & zd, set())

    def test_every_zero_day_family_is_in_test(self):
        zd = set(config.get()["zero_day_classes"])
        self.assertEqual(set(_y("test").tolist()) & zd, zd)

    def test_known_classes_file_matches_train(self):
        known = set(np.load(os.path.join(P, "known_classes.npy"), allow_pickle=True).tolist())
        self.assertEqual(known, set(_y("train").tolist()))
        self.assertEqual(len(known), 9)

    def test_split_sizes(self):
        self.assertEqual([len(_y(s)) for s in ("train", "val", "test")],
                         [883_796, 110_475, 114_658])


@unittest.skipUnless(HAVE_SPLIT, "paper split arrays not present")
class FeatureBasis(unittest.TestCase):
    """INVARIANT: the 68-feature basis every result is defined on."""

    def test_feature_count_is_68(self):
        for split in ("train", "val", "test"):
            with self.subTest(split=split):
                X = np.load(os.path.join(P, "X_%s.npy" % split), mmap_mode="r")
                self.assertEqual(X.shape[1], 68)

    def test_behaviour_indices_match_feature_order(self):
        import behavior
        cols = list(pd.read_csv(os.path.join(paths.PROCESSED, "features_train.csv"),
                                nrows=0).columns)
        expect = {"dst_port": "Destination Port", "flow_duration": "Flow Duration",
                  "flow_pkts_s": "Flow Packets/s", "pkt_len_mean": "Packet Length Mean",
                  "pkt_len_std": "Packet Length Std", "urg": "URG Flag Count"}
        for key, name in expect.items():
            with self.subTest(key=key):
                self.assertEqual(cols[behavior.IDX[key]], name)

    def test_feature_matrix_is_finite(self):
        X = np.load(os.path.join(P, "X_train.npy"), mmap_mode="r")
        self.assertTrue(np.isfinite(features.transform(np.asarray(X[:50_000]))).all())


@unittest.skipUnless(HAVE_SPLIT and os.path.exists(SCALER), "scaler or split not present")
class TransformBoundary(unittest.TestCase):
    """INVARIANT: the saved scaler was fitted on the training split and nothing else."""

    def test_scaler_is_fitted_on_train_only(self):
        with open(SCALER, "rb") as f:
            sc = pickle.load(f)
        tfm = config.get()["protocol"]["feature_transform"]
        tr = features.transform(np.load(os.path.join(P, "X_train.npy")), tfm)
        np.testing.assert_allclose(sc.mean_, tr.mean(0), rtol=1e-6, atol=1e-8)
        self.assertEqual(sc.n_samples_seen_, len(tr))
        # and it is NOT the train+test statistic
        te = features.transform(np.load(os.path.join(P, "X_test.npy")), tfm)
        pooled = np.vstack([tr, te]).mean(0)
        self.assertFalse(np.allclose(sc.mean_, pooled, rtol=1e-6, atol=1e-8))


@unittest.skipUnless(HAVE_SPLIT, "paper split arrays not present")
class DuplicateOverlap(unittest.TestCase):
    """PINNED (audit F-10): exact train/test duplicates, recomputed from the arrays."""

    @classmethod
    def setUpClass(cls):
        def h(X):
            return [hashlib.blake2b(r.tobytes(), digest_size=16).digest() for r in X]
        tr = set(h(np.load(os.path.join(P, "X_train.npy"))))
        cls.y = _y("test")
        cls.dup = np.fromiter((x in tr for x in h(np.load(os.path.join(P, "X_test.npy")))),
                              bool, len(cls.y))

    def test_overall_rate_is_pinned(self):
        self.assertEqual(int(self.dup.sum()), 19_513)

    def test_zero_day_families_have_no_training_duplicate(self):
        # INVARIANT inside the pinned block: this is why the headline metric is
        # unaffected by the duplicate defect.
        for fam in config.get()["zero_day_classes"]:
            with self.subTest(family=fam):
                self.assertEqual(int(self.dup[self.y == fam].sum()), 0)


@unittest.skipUnless(HAVE_META, "paper split meta tables not present")
class GroupAndTimeOverlap(unittest.TestCase):
    """PINNED (audit F-02, F-03): the split is neither grouped nor chronological."""

    def test_flow_id_overlap_is_pinned(self):
        tr = set(pd.read_csv(os.path.join(P, "meta_train.csv"), usecols=["Flow ID"])["Flow ID"].astype(str))
        te = pd.read_csv(os.path.join(P, "meta_test.csv"), usecols=["Flow ID"])["Flow ID"].astype(str)
        frac = float(np.mean([f in tr for f in te]))
        self.assertAlmostEqual(frac, 0.5488, places=4)

    def test_web_attack_zero_day_sessions_all_recur_in_train(self):
        tr = set(pd.read_csv(os.path.join(P, "meta_train.csv"), usecols=["Flow ID"])["Flow ID"].astype(str))
        te = pd.read_csv(os.path.join(P, "meta_test.csv"), usecols=["Flow ID"])["Flow ID"].astype(str).values
        y = _y("test")
        for fam in ("Web Attack Brute Force", "Web Attack XSS", "Web Attack Sql Injection"):
            with self.subTest(family=fam):
                self.assertTrue(all(f in tr for f in te[y == fam]))

    def test_bot_sessions_never_recur_in_train(self):
        # The paper contrasts this with the web families (Appendix A).
        tr = set(pd.read_csv(os.path.join(P, "meta_train.csv"), usecols=["Flow ID"])["Flow ID"].astype(str))
        te = pd.read_csv(os.path.join(P, "meta_test.csv"), usecols=["Flow ID"])["Flow ID"].astype(str).values
        self.assertFalse(any(f in tr for f in te[_y("test") == "Bot"]))

    def test_test_lies_inside_train_time_range(self):
        import timeline
        tr, te = timeline.load_timestamps("train"), timeline.load_timestamps("test")
        inside = float(np.asarray((te >= tr.min()) & (te <= tr.max())).mean())
        self.assertEqual(inside, 1.0)


@unittest.skipUnless(os.path.exists(RECORD), "split_integrity.json not generated")
class Record(unittest.TestCase):
    """The persisted record agrees with the pins above and names the known defects."""

    @classmethod
    def setUpClass(cls):
        with open(RECORD, encoding="utf-8") as f:
            cls.r = json.load(f)

    def test_record_boundary(self):
        self.assertEqual(self.r["zero_day_in_train"], [])
        self.assertEqual(self.r["zero_day_in_val"], [])
        self.assertEqual(self.r["n_features"], 68)

    def test_record_pins(self):
        self.assertAlmostEqual(self.r["duplicates"]["fraction"], 0.1702, places=4)
        self.assertAlmostEqual(self.r["group_overlap"]["flow_id_fraction"], 0.5488, places=4)
        self.assertEqual(self.r["temporal"]["test_inside_train_range"], 1.0)
        self.assertAlmostEqual(self.r["benign"]["undersample_factor"], 4.112, places=3)

    def test_constant_column_finding_is_pinned(self):
        """F-15: only two dropped columns vary, only on benign rows, and the kept
        `URG Flag Count` carries the same bit on every one of them."""
        cc = self.r["constant_columns"]
        if not cc.get("checked_on_full_capture"):
            self.skipTest("raw CSVs were not present when the record was written")
        nc = cc["non_constant_on_full_capture"]
        self.assertEqual(sorted(nc), ["CWE Flag Count", "Fwd URG Flags"])
        for col, e in nc.items():
            with self.subTest(column=col):
                self.assertEqual(e["labels"], {"BENIGN": 315})
                self.assertEqual(e["urg_flag_count_also_1"], e["rows"])


if __name__ == "__main__":
    unittest.main()
