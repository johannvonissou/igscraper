import time
from urllib.parse import urljoin

from patchright.async_api import Error as PlaywrightError
from patchright.async_api import TimeoutError as PlaywrightTimeoutError

from igscraper.constants import (
    ACCOUNT_SEL_USERNAME,
    ACCOUNT_SLEEP_INTER,
    ACCOUNT_TO_PROFILE,
    LOGIN_SLEEP_POLL,
    MAIN_PAGE,
    NAVIGATION_TO_CLICK,
    asleep,
    debug,
    error,
    info,
)


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


async def goto_page(page, url, *, wait_until="domcontentloaded"):
    await page.goto(url, wait_until=wait_until)


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

        await asleep(ACCOUNT_SLEEP_INTER)

        return True

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


__all__ = ["ProfilePage", "click_first", "goto_page", "is_present"]
