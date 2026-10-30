from functools import cache

from igscraper.constants import JS_DIR


@cache
def script(name):
    return (JS_DIR / f"{name}.js").read_text(encoding="utf-8")


__all__ = ["script"]
