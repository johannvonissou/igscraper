import time
from urllib.parse import parse_qs, urlparse

from patchright.async_api import Error as PlaywrightError

from igscraper.constants import (
    ACCOUNT_BIO_MORE_TEXT,
    ACCOUNT_FOLLOW_TEXTS,
    ACCOUNT_FOLLOWED_TEXT,
    ACCOUNT_FOLLOWERS_TEXT,
    ACCOUNT_FOLLOWING_TEXT,
    ACCOUNT_NAME_LINE_INDEX,
    ACCOUNT_OWN_TEXT,
    ACCOUNT_POSTS_TEXT,
    ACCOUNT_PRIVATE_TEXT,
    ACCOUNT_REQUESTED_CANCEL_TEXT,
    ACCOUNT_REQUESTED_TEXT,
    ACCOUNT_SEL_ADDRESS,
    ACCOUNT_SEL_BIO,
    ACCOUNT_SEL_BIO_LINK,
    ACCOUNT_SEL_BUTTONS,
    ACCOUNT_SEL_FOLLOWERS,
    ACCOUNT_SEL_HEADER,
    ACCOUNT_SEL_POSTS,
    ACCOUNT_SEL_USERNAME,
    ACCOUNT_SLEEP_INTER,
    ACCOUNT_STATS_SUFFIXES,
    ACCOUNT_TO_ATTRIBUTE,
    ACCOUNT_TO_BIO_CLICK,
    ACCOUNT_TO_FOLLOW,
    ACCOUNT_TO_FOLLOW_CLICK,
    asleep,
    error,
    info,
    success,
    warn,
)
from igscraper.errors import guard
from igscraper.navigation import ProfilePage


class Account(ProfilePage):
    @guard
    async def follow(self, username):
        username = await self.open_profile(username)

        if username is None:
            return False

        texts = await self._button_texts()
        followed = self._has_followed(texts)
        requested = self._has_requested(texts)

        if followed or requested:
            state = "déjà suivi(e)" if followed else "demande d'abonnement en attente"
            warn(f"@{username} : {state}.")

            return True

        index = self._find_button(texts, ACCOUNT_FOLLOW_TEXTS)

        if index is None:
            error(f"Bouton d'abonnement introuvable pour @{username} : compte bloqué ou sélecteur à revoir.")

            return False

        button = self._page.locator(ACCOUNT_SEL_BUTTONS).nth(index)

        info(f"Clic sur le bouton « {texts[index]} » pour @{username}.")

        try:
            await button.click(timeout=ACCOUNT_TO_FOLLOW_CLICK)
        except PlaywrightError:
            error(f"@{username} : clic sur le bouton d'abonnement impossible.")

            return False

        if not await self._wait_follow_state():
            error(f"@{username} : état d'abonnement non confirmé après le clic.")

            return False

        if await self._is_followed():
            success(f"Abonnement confirmé : @{username} est suivi(e).")
        else:
            success(f"Demande d'abonnement envoyée à @{username} (compte privé) : en attente de validation.")

        return True

    @guard
    async def retrieve(self, username):
        username = await self.open_profile(username)

        if username is None:
            return None

        return await self._collect(username)

    @staticmethod
    def _decode_bio_link(href):
        parsed = urlparse(href)

        if parsed.netloc != "l.instagram.com":
            return href

        return parse_qs(parsed.query).get("u", [href])[0]

    @staticmethod
    def _clean_lines(text):
        return list(dict.fromkeys(line.strip() for line in text.split("\n") if line.strip()))

    @staticmethod
    def _get_name(lines):
        if len(lines) <= ACCOUNT_NAME_LINE_INDEX:
            return ""

        name = lines[ACCOUNT_NAME_LINE_INDEX]

        if any(name.endswith(suffix) for suffix in ACCOUNT_STATS_SUFFIXES):
            return ""

        return name

    @staticmethod
    def _count_to_int(text):
        if text is None:
            return None

        cleaned = text.replace("\u202f", "").replace("\u00a0", "").replace(" ", "").replace(",", "")

        return int(cleaned) if cleaned.isdigit() else None

    @staticmethod
    def _has_followed(texts):
        return ACCOUNT_FOLLOWED_TEXT in texts or ACCOUNT_OWN_TEXT in texts

    @staticmethod
    def _has_requested(texts):
        return ACCOUNT_REQUESTED_TEXT in texts or ACCOUNT_REQUESTED_CANCEL_TEXT in texts

    @staticmethod
    def _find_button(texts, wanted):
        return next((index for index, text in enumerate(texts) if text in wanted), None)

    async def _collect(self, username):
        await self._expand_bio()

        section = self._page.locator(ACCOUNT_SEL_USERNAME).first.locator("xpath=ancestor::section[1]")
        lines = self._clean_lines(await section.inner_text())

        account = {
            "username": username,
            "name": self._get_name(lines),
            "appearsPrivate": await self._appears_private(),
            "isFollowed": await self._is_followed(),
            "postsCount": self._line_to_count(lines, ACCOUNT_POSTS_TEXT),
            "followersCount": await self._get_followers(lines),
            "followingCount": self._line_to_count(lines, ACCOUNT_FOLLOWING_TEXT),
            "bio": await self._get_bio(),
            "address": await self._get_address(),
            "url": await self._get_bio_link(),
            "latestPosts": await self._get_posts(username),
        }

        info(
            f"Profil @{username} récupéré "
            f"({account['followersCount'] or 0} followers, {len(account['latestPosts'])} posts).",
        )

        return account

    async def _get_followers(self, lines):
        title = self._page.locator(ACCOUNT_SEL_FOLLOWERS).first

        if await title.count():
            try:
                value = self._count_to_int(await title.get_attribute("title", timeout=ACCOUNT_TO_ATTRIBUTE))
            except PlaywrightError:
                value = None

            if value is not None:
                return value

        return self._line_to_count(lines, ACCOUNT_FOLLOWERS_TEXT)

    async def _get_bio(self):
        bio = self._page.locator(ACCOUNT_SEL_BIO).first

        if not await bio.count():
            return ""

        try:
            return (await bio.inner_text()).strip()
        except PlaywrightError:
            return ""

    async def _get_address(self):
        address = self._page.locator(ACCOUNT_SEL_ADDRESS).first

        if not await address.count():
            return None

        try:
            return (await address.inner_text()).strip() or None
        except PlaywrightError:
            return None

    async def _get_bio_link(self):
        link = self._page.locator(ACCOUNT_SEL_BIO_LINK).first

        if not await link.count():
            return None

        try:
            href = await link.get_attribute("href", timeout=ACCOUNT_TO_ATTRIBUTE)
        except PlaywrightError:
            return None

        return self._decode_bio_link(href) if href else None

    async def _expand_bio(self):
        plus = self._page.locator(ACCOUNT_SEL_HEADER).get_by_text(ACCOUNT_BIO_MORE_TEXT, exact=True)

        if not await plus.count():
            return False

        try:
            await plus.first.click(timeout=ACCOUNT_TO_BIO_CLICK)
        except PlaywrightError:
            return False

        info("Bio étendue via le bouton « plus ».")

        await asleep(ACCOUNT_SLEEP_INTER)

        return True

    async def _get_posts(self, username):
        posts = []
        seen = set()

        for anchor in await self._page.locator(ACCOUNT_SEL_POSTS).all():
            href = await anchor.get_attribute("href")

            if not href or href in seen or not href.startswith(f"/{username}/"):
                continue

            seen.add(href)

            image = anchor.locator("img").first

            if await image.count():
                description = (await image.get_attribute("alt")) or ""
                image_url = await image.get_attribute("src")
            else:
                description = ""
                image_url = None

            posts.append({"description": description, "imageUrl": image_url})

        return posts

    def _line_to_count(self, lines, suffix):
        line = next((line for line in lines if line.endswith(suffix)), None)

        if line is None:
            return None

        return self._count_to_int(line[: -len(suffix)].strip())

    async def _appears_private(self):
        return await self._page.get_by_text(ACCOUNT_PRIVATE_TEXT).count() > 0

    async def _button_texts(self):
        return [text.strip() for text in await self._page.locator(ACCOUNT_SEL_BUTTONS).all_inner_texts()]

    async def _is_followed(self):
        return self._has_followed(await self._button_texts())

    async def _is_requested(self):
        return self._has_requested(await self._button_texts())

    async def _wait_follow_state(self):
        deadline = time.monotonic() + ACCOUNT_TO_FOLLOW

        while time.monotonic() < deadline:
            if await self._is_followed() or await self._is_requested():
                return True

            await asleep(ACCOUNT_SLEEP_INTER)

        return False


__all__ = ["Account"]
