import time
from urllib.parse import parse_qs, urlparse

from patchright.async_api import Error as PlaywrightError

from igscraper.constants import (
    ACCOUNT_BIO_MORE_TEXT,
    ACCOUNT_FOLLOW_MUTATION_HINTS,
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
    ACCOUNT_SEL_SECTION,
    ACCOUNT_SEL_USERNAME,
    ACCOUNT_STATS_SUFFIXES,
    ACCOUNT_TO_BIO_CLICK,
    ACCOUNT_TO_BIO_EXPAND,
    ACCOUNT_TO_FOLLOW,
    ACCOUNT_TO_FOLLOW_CLICK,
    ACCOUNT_TO_FOLLOW_RESPONSE,
    ACCOUNT_TO_PROFILE_READY,
    POLL_DELAY_GROWTH,
    POLL_DELAY_MAX,
    POLL_DELAY_START,
    asleep,
    debug,
    error,
    info,
    success,
    warn,
)
from igscraper.errors import guard
from igscraper.navigation import ProfilePage, wait_dom
from igscraper.scripts import script


class Account(ProfilePage):
    def __init__(self, page):
        super().__init__(page)

        self._buttons = None

    @guard
    async def follow(self, username):
        self._buttons = None
        username = await self.open_profile(username)

        if username is None:
            return False

        texts = await self._follow_texts()
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

        confirmed = await self._click_follow(button, username)

        if confirmed is False:
            return False

        texts = await self._wait_follow_state(confirmed) or []
        followed = self._has_followed(texts)
        requested = self._has_requested(texts) or (confirmed and await self._appears_private())

        if not followed and not requested:
            error(f"@{username} : état d'abonnement non confirmé après le clic.")

            return False

        if followed:
            success(f"Abonnement confirmé : @{username} est suivi(e).")
        else:
            success(f"Demande d'abonnement envoyée à @{username} (compte privé) : en attente de validation.")

        return True

    @guard
    async def retrieve(self, username):
        self._buttons = None
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

    @staticmethod
    def _is_follow_response(response):
        request = response.request

        if request.method != "POST" or "/graphql" not in request.url:
            return False

        try:
            body = (request.post_data or "").lower()
        except PlaywrightError:
            return False

        return any(hint in body for hint in ACCOUNT_FOLLOW_MUTATION_HINTS)

    async def _collect(self, username):
        await self._expand_bio()

        overview = await self._page.evaluate(script("account_overview"), self._overview_args(username))
        lines = self._clean_lines(overview["sectionText"])
        texts = overview["buttonTexts"]
        followers = self._count_to_int(overview["followersTitle"])

        if followers is None:
            followers = self._line_to_count(lines, ACCOUNT_FOLLOWERS_TEXT)

        bio_link = overview["bioLink"]

        self._buttons = texts

        account = {
            "username": username,
            "name": self._get_name(lines),
            "appearsPrivate": overview["appearsPrivate"],
            "isFollowed": self._has_followed(texts),
            "postsCount": self._line_to_count(lines, ACCOUNT_POSTS_TEXT),
            "followersCount": followers,
            "followingCount": self._line_to_count(lines, ACCOUNT_FOLLOWING_TEXT),
            "bio": overview["bio"],
            "address": overview["address"],
            "url": self._decode_bio_link(bio_link) if bio_link else None,
            "latestPosts": overview["posts"],
        }

        info(
            f"Profil @{username} récupéré "
            f"({account['followersCount'] or 0} followers, {len(account['latestPosts'])} posts).",
        )

        return account

    @staticmethod
    def _overview_args(username):
        return {
            "username": username,
            "usernameSelector": ACCOUNT_SEL_USERNAME,
            "sectionSelector": ACCOUNT_SEL_SECTION,
            "followerSelector": ACCOUNT_SEL_FOLLOWERS,
            "bioSelector": ACCOUNT_SEL_BIO,
            "addressSelector": ACCOUNT_SEL_ADDRESS,
            "bioLinkSelector": ACCOUNT_SEL_BIO_LINK,
            "privateText": ACCOUNT_PRIVATE_TEXT,
            "postSelector": ACCOUNT_SEL_POSTS,
            "buttonSelector": ACCOUNT_SEL_BUTTONS,
        }

    async def _expand_bio(self):
        plus = self._page.locator(ACCOUNT_SEL_HEADER).get_by_text(ACCOUNT_BIO_MORE_TEXT, exact=True)

        if not await plus.count():
            return False

        before = await self._page.evaluate(script("text_length"), ACCOUNT_SEL_BIO)

        try:
            await plus.first.click(timeout=ACCOUNT_TO_BIO_CLICK)
        except PlaywrightError:
            return False

        info("Bio étendue via le bouton « plus ».")

        await wait_dom(
            self._page,
            "text_longer",
            {"selector": ACCOUNT_SEL_BIO, "length": before},
            timeout_ms=ACCOUNT_TO_BIO_EXPAND,
        )

        return True

    async def _click_follow(self, button, username):
        clicked = False
        answered = False

        try:
            async with self._page.expect_response(
                self._is_follow_response,
                timeout=ACCOUNT_TO_FOLLOW_RESPONSE,
            ) as awaited:
                await button.click(timeout=ACCOUNT_TO_FOLLOW_CLICK)
                clicked = True

                await awaited.value

                answered = True
        except PlaywrightError:
            pass

        if not clicked:
            error(f"@{username} : clic sur le bouton d'abonnement impossible.")

            return False

        if not answered:
            debug(f"@{username} : réponse d'abonnement non observée, vérification DOM.")

            return None

        return True

    async def _follow_texts(self):
        deadline = time.monotonic() + ACCOUNT_TO_PROFILE_READY / 1000
        delay = POLL_DELAY_START
        wanted = (
            *ACCOUNT_FOLLOW_TEXTS,
            ACCOUNT_FOLLOWED_TEXT,
            ACCOUNT_OWN_TEXT,
            ACCOUNT_REQUESTED_TEXT,
            ACCOUNT_REQUESTED_CANCEL_TEXT,
        )

        while True:
            texts = await self._button_texts(refresh=True)

            if any(text in wanted for text in texts):
                return texts

            if time.monotonic() >= deadline:
                return texts

            await asleep(delay)

            delay = min(delay * POLL_DELAY_GROWTH, POLL_DELAY_MAX)

    async def _wait_follow_state(self, confirmed):
        timeout = ACCOUNT_TO_FOLLOW_RESPONSE / 1000 if confirmed else ACCOUNT_TO_FOLLOW
        deadline = time.monotonic() + timeout
        delay = POLL_DELAY_START

        while True:
            texts = await self._button_texts(refresh=True)

            if self._has_followed(texts) or self._has_requested(texts):
                return texts

            if time.monotonic() >= deadline:
                return texts if confirmed else None

            await asleep(delay)

            delay = min(delay * POLL_DELAY_GROWTH, POLL_DELAY_MAX)

    def _line_to_count(self, lines, suffix):
        line = next((line for line in lines if line.endswith(suffix)), None)

        if line is None:
            return None

        return self._count_to_int(line[: -len(suffix)].strip())

    async def _appears_private(self):
        return await self._page.get_by_text(ACCOUNT_PRIVATE_TEXT).count() > 0

    async def _button_texts(self, *, refresh=False):
        if refresh or self._buttons is None:
            self._buttons = await self._page.evaluate(script("button_texts"), ACCOUNT_SEL_BUTTONS)

        return self._buttons

    async def _is_followed(self):
        return self._has_followed(await self._button_texts())

    async def _is_requested(self):
        return self._has_requested(await self._button_texts())


__all__ = ["Account"]
