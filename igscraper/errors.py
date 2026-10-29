from functools import wraps

from patchright.async_api import Error as PlaywrightError

from igscraper.constants import ERROR_MAX_DETAIL, error


class IGScraperError(Exception):
    pass


class BrowserError(IGScraperError):
    pass


class LoginError(IGScraperError):
    pass


class ChallengeRequiredError(LoginError):
    pass


class LoginRequiredError(IGScraperError):
    pass


class ScrapeError(IGScraperError):
    pass


def summarize(exc):
    message = (str(exc) or "").strip()
    first = message.split("\n", 1)[0] if message else ""

    if len(first) > ERROR_MAX_DETAIL:
        first = first[:ERROR_MAX_DETAIL] + "…"

    return f"{type(exc).__name__} : {first}" if first else type(exc).__name__


def guard(fn):

    @wraps(fn)
    async def wrapper(*args, **kwargs):
        try:
            return await fn(*args, **kwargs)
        except IGScraperError:
            raise
        except (PlaywrightError, OSError) as exc:
            error(f"Exception interceptée : {summarize(exc)}")

            return None

    return wrapper
