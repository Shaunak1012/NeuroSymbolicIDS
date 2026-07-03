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
        with open(_PATH, "r") as f:
            _CFG = yaml.safe_load(f)
    return _CFG
