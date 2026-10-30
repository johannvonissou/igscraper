import re
import time
from inspect import isawaitable
from random import random, uniform
from urllib.parse import urljoin

from patchright.async_api import Error as PlaywrightError
from patchright.async_api import TimeoutError as PlaywrightTimeoutError

from igscraper.constants import (
    ACCOUNT_COUNT_MULTIPLIERS,
    ACCOUNT_COUNT_PATTERN,
    ACCOUNT_SEL_USERNAME,
    ACCOUNT_TO_PROFILE,
    ACCOUNT_TO_PROFILE_READY,
    BROWSER_DOM_READY,
    LOGIN_SLEEP_POLL,
    MAIN_PAGE,
    NAVIGATION_TO_CLICK,
    POLL_DELAY_GROWTH,
    POLL_DELAY_MAX,
    POLL_DELAY_START,
    PROFILE_READY_MARKERS,
    TYPE_PAUSE_CHARS,
    asleep,
    debug,
    error,
    info,
)
from igscraper.scripts import script


async def click_first(page, selectors, *, timeout_ms, label):
    deadline = time.monotonic() + max(timeout_ms, 0) / 1000

    while True:
        for selector in selectors:
            locator = page.locator(selector).first

            if not await locator.count():
                continue

            try:
                await locator.click(timeout=NAVIGATION_TO_CLICK)
            except PlaywrightError:
                continue

            info(f"{label} : clic effectué.")

            return True

        if time.monotonic() >= deadline:
            break

        await asleep(LOGIN_SLEEP_POLL)

    debug(f"{label} : aucun élément correspondant.")

    return False


async def is_present(page, selector):
    return await page.locator(selector).count() > 0


async def goto_page(page, url, *, wait_until=BROWSER_DOM_READY):
    await page.goto(url, wait_until=wait_until)


async def poll_for(predicate, *, timeout_s, delay=POLL_DELAY_START):
    deadline = time.monotonic() + max(timeout_s, 0)

    while True:
        result = predicate()

        if isawaitable(result):
            result = await result

        if result:
            return True

        if time.monotonic() >= deadline:
            return False

        await asleep(delay)

        delay = min(delay * POLL_DELAY_GROWTH, POLL_DELAY_MAX)


async def wait_dom(page, name, arg=None, *, timeout_ms):
    try:
        await page.wait_for_function(script(name), arg=arg, timeout=timeout_ms)
    except PlaywrightTimeoutError:
        return False

    return True


async def type_text(  # noqa: PLR0913
    locator,
    text,
    *,
    min_ms,
    max_ms,
    pause_ms,
    pause_chance,
    pause_chars=TYPE_PAUSE_CHARS,
):
    for char in text:
        await locator.press_sequentially(char)

        delay = uniform(min_ms, max_ms) / 1000  # noqa: S311

        if char in pause_chars and random() < pause_chance:  # noqa: S311
            delay += uniform(*pause_ms) / 1000  # noqa: S311

        await asleep(delay)


def parse_count(text):
    if text is None:
        return None

    cleaned = str(text).replace("\u202f", "").replace("\u00a0", "").replace(" ", "")
    match = re.fullmatch(ACCOUNT_COUNT_PATTERN, cleaned)

    if match is None:
        return None

    number, unit = match.groups()

    if not unit:
        digits = number.replace(",", "").replace(".", "")

        return int(digits) if digits.isdigit() else None

    try:
        value = float(number.replace(",", "."))
    except ValueError:
        return None

    return round(value * ACCOUNT_COUNT_MULTIPLIERS[unit.lower()])


class ProfilePage:
    def __init__(self, page):
        self._page = page

    async def open_profile(self, username):
        username = self.normalize_username(username)

        if not username:
            error("Nom d'utilisateur vide.")

            return None

        url = self.profile_url(username)

        await goto_page(self._page, url)

        info(f"Page de profil ouverte : {url}.")

        if not await self.wait_profile():
            return None

        return await self.current_username()

    async def wait_profile(self):
        try:
            await self._page.locator(ACCOUNT_SEL_USERNAME).first.wait_for(state="visible", timeout=ACCOUNT_TO_PROFILE)
        except PlaywrightTimeoutError:
            error(f"Profil '{ACCOUNT_SEL_USERNAME}' introuvable : compte inexistant, bloqué, ou sélecteur à revoir.")

            return False

        await self.wait_profile_ready()

        return True

    async def wait_profile_ready(self):
        ready = await wait_dom(
            self._page,
            "profile_ready",
            {"selector": "main header", "markers": list(PROFILE_READY_MARKERS)},
            timeout_ms=ACCOUNT_TO_PROFILE_READY,
        )

        debug("Profil prêt." if ready else "Profil toujours en cours de chargement (continuation).")

        return ready

    async def current_username(self):
        return (await self._page.locator(ACCOUNT_SEL_USERNAME).first.inner_text()).strip()

    @property
    def page(self):
        return self._page

    @classmethod
    def profile_url(cls, username):
        return urljoin(f"{MAIN_PAGE}/", f"{cls.normalize_username(username)}/")

    @staticmethod
    def normalize_username(username):
        return (username or "").strip().lstrip("@").strip("/")


__all__ = [
    "ProfilePage",
    "click_first",
    "goto_page",
    "is_present",
    "parse_count",
    "poll_for",
    "type_text",
    "wait_dom",
]
