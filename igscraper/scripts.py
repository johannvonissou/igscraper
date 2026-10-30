from functools import cache
from pathlib import Path

JS_DIR = Path(__file__).resolve().parent / "js"


@cache
def script(name):
    return (JS_DIR / f"{name}.js").read_text(encoding="utf-8")


__all__ = ["script"]
