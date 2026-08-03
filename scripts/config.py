"""
Loads the central config.yaml. Import and use `config.get()`.

    import config
    cfg = config.get()
    seed = cfg["seed"]
"""
import os
import yaml

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PATH = os.path.join(_ROOT, "config.yaml")
_CFG = None


def get():
    global _CFG
    if _CFG is None:
        # encoding is explicit: on Windows the default is cp1252, which raises
        # UnicodeDecodeError the moment a non-ASCII character appears in config.yaml
        # (hit 2026-08-03 when a comment gained a "warning" glyph).
        with open(_PATH, "r", encoding="utf-8") as f:
            _CFG = yaml.safe_load(f)
    return _CFG
