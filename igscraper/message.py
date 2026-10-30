import json
import time
from contextlib import suppress

from patchright.async_api import Error as PlaywrightError

from igscraper.constants import (
    MESSAGE_CONTACT_TEXTS,
    MESSAGE_CONTENT_PLACEHOLDERS,
    MESSAGE_GRAPHQL_FRAGMENT,
    MESSAGE_HISTORY_ROUNDS,
    MESSAGE_HISTORY_STABLE,
    MESSAGE_MEDIA_PLACEHOLDER,
    MESSAGE_PAYLOAD_KEYS,
    MESSAGE_SCROLL_COMPOSER_GAP,
    MESSAGE_SCROLL_DELTA,
    MESSAGE_SCROLL_STEPS,
    MESSAGE_SEL_ARTICLE,
    MESSAGE_SEL_BUTTONS,
    MESSAGE_SEL_CLOSE_CANDIDATES,
    MESSAGE_SEL_COMPOSER_CANDIDATES,
    MESSAGE_SEL_THREAD,
    MESSAGE_SEND_POLL_MAX,
    MESSAGE_SLEEP_POLL,
    MESSAGE_SLEEP_SEND_POLL,
    MESSAGE_TIMESTAMP_MICROSECONDS,
    MESSAGE_TIMESTAMP_MILLISECONDS,
    MESSAGE_TO_CHAT_WINDOW,
    MESSAGE_TO_CLOSE,
    MESSAGE_TO_PAGE,
    POLL_DELAY_GROWTH,
    POLL_DELAY_MAX,
    POLL_DELAY_START,
    TYPE_PAUSE_CHANCE,
    TYPE_PAUSE_MS,
    TYPE_SLEEP_MAX_MS,
    TYPE_SLEEP_MIN_MS,
    asleep,
    debug,
    error,
    info,
    success,
    warn,
)
from igscraper.errors import guard
from igscraper.navigation import ProfilePage, poll_for, type_text, wait_dom
from igscraper.scripts import script


class Message(ProfilePage):
    def __init__(self, page):
        super().__init__(page)

        self._payloads = []
        self._listener = self._capture
        self._reset()

        page.on("response", self._listener)

    @guard
    async def get_messages(self, username):
        username = await self.open_profile(username)

        if username is None:
            return False

        if await self._open_chat() is None:
            return False

        try:
            messages = await self._collect_history(username)
        finally:
            await self._close_chat()

        if messages is None:
            return False

        info(f"Messages récupérés pour @{username} : {len(messages)}.")

        return self._as_payload(username, messages)

    @guard
    async def send_message(self, username, message, *, history=False):
        if not message or not message.strip():
            error("Message vide.")

            return False

        username = await self.open_profile(username)

        if username is None:
            return False

        composer = await self._open_chat()

        if composer is None:
            return False

        sent_at = int(time.time())
        messages = None

        try:
            sent = await self._send(composer, message)

            if sent:
                success(f"Message envoyé à @{username}.")

            if sent and history:
                messages = await self._collect_history(username)
        finally:
            await self._close_chat()

        if not sent:
            return False

        if history and messages is None:
            warn("Message envoyé, mais l'historique n'a pas pu être relu.")

        if not history or messages is None:
            return self._as_payload(username, [], sent=True)

        messages = self._with_sent(messages, message, sent_at)

        info(f"Historique récupéré après envoi : {len(messages)} messages.")

        return self._as_payload(username, messages, sent=True)

    async def detach(self):
        with suppress(PlaywrightError):
            self._page.remove_listener("response", self._listener)

    @staticmethod
    def _sender(node, users, viewer):
        sender = node.get("sender") or {}

        username = sender.get("username")

        if not username:
            username = (sender.get("user_dict") or {}).get("username")

        if not username:
            fbid = node.get("sender_fbid") or sender.get("id")

            if fbid:
                username = users.get(str(fbid))

        if not username:
            username = users.get(str(sender.get("igid")))

        if viewer and sender.get("igid"):
            return username, str(sender["igid"]) == str(viewer)

        return username, None

    @staticmethod
    def _content(node):
        kind = str(node.get("content_type") or "").upper()

        if not kind or kind == "TEXT":
            return node.get("text_body") or node.get("text") or ""

        return MESSAGE_CONTENT_PLACEHOLDERS.get(kind, MESSAGE_MEDIA_PLACEHOLDER)

    @staticmethod
    def _unix_seconds(value):
        try:
            stamp = int(value)
        except (TypeError, ValueError):
            return None

        if stamp >= MESSAGE_TIMESTAMP_MICROSECONDS:
            return stamp // 1_000_000

        if stamp >= MESSAGE_TIMESTAMP_MILLISECONDS:
            return stamp // 1_000

        return stamp

    @staticmethod
    def _as_payload(username, messages, sent=None):
        payload = {"username": username}

        if sent is not None:
            payload["sent"] = sent

        payload["messages"] = [{"index": index + 1, **message} for index, message in enumerate(messages)]

        return payload

    def _with_sent(self, messages, message, sent_at):
        wanted = message.strip()

        for item in messages:
            if item["isSelf"] and (item["content"] or "").strip() == wanted and item["timestamp"] >= sent_at - 120:
                return messages

        viewer = self._users.get(str(self._viewer)) if self._viewer is not None else None
        echo = {"timestamp": sent_at, "sender": viewer, "isSelf": True, "content": message}

        return sorted([*messages, echo], key=lambda m: m["timestamp"])

    def _reset(self):
        self._payloads.clear()

        self._processed = 0
        self._messages = []
        self._users = {}
        self._viewer = None
        self._has_next = False
        self._found = False

    async def _open_chat(self):
        self._reset()

        texts, index = await self._contact()

        if index is None:
            error(f"Bouton de contact introuvable ({', '.join(MESSAGE_CONTACT_TEXTS)}).")

            return None

        info(f"Clic sur le bouton « {texts[index]} ».")

        await self._page.locator(MESSAGE_SEL_BUTTONS).nth(index).click()

        return await self._composer()

    async def _contact(self):
        deadline = time.monotonic() + MESSAGE_TO_CHAT_WINDOW / 1000
        delay = POLL_DELAY_START

        while True:
            texts = await self._page.evaluate(script("button_texts"), MESSAGE_SEL_BUTTONS)
            index = next((i for i, text in enumerate(texts) if text in MESSAGE_CONTACT_TEXTS), None)

            if index is not None:
                return texts, index

            if time.monotonic() >= deadline:
                return texts, None

            await asleep(delay)

            delay = min(delay * POLL_DELAY_GROWTH, POLL_DELAY_MAX)

    async def _composer(self):
        selector = ", ".join(MESSAGE_SEL_COMPOSER_CANDIDATES)
        composer = self._page.locator(selector).first

        try:
            await composer.wait_for(state="visible", timeout=MESSAGE_TO_CHAT_WINDOW)
        except PlaywrightError:
            error(f"Fenêtre de messagerie non apparue ({MESSAGE_TO_CHAT_WINDOW} ms) : blocage ou compte non joignable.")

            return None

        return composer

    async def _send(self, composer, message):
        await composer.click()
        await type_text(
            composer,
            message,
            min_ms=TYPE_SLEEP_MIN_MS,
            max_ms=TYPE_SLEEP_MAX_MS,
            pause_ms=TYPE_PAUSE_MS,
            pause_chance=TYPE_PAUSE_CHANCE,
        )
        await composer.press("Enter")

        return await self._wait_sent(message)

    async def _close_chat(self):
        composer = self._page.locator(", ".join(MESSAGE_SEL_COMPOSER_CANDIDATES)).first

        try:
            await self._page.keyboard.press("Escape")
            await composer.wait_for(state="hidden", timeout=MESSAGE_TO_CLOSE)
        except PlaywrightError:
            pass
        else:
            return

        close = self._page.locator(", ".join(MESSAGE_SEL_CLOSE_CANDIDATES)).last

        if not await close.count():
            debug("Bouton de fermeture de la conversation introuvable.")

            return

        try:
            await close.click(timeout=MESSAGE_TO_CHAT_WINDOW)
        except PlaywrightError:
            return

        with suppress(PlaywrightError):
            await composer.wait_for(state="hidden", timeout=MESSAGE_TO_CLOSE)

    async def _capture(self, response):
        url = response.url

        if "/api/graphql" not in url and "/graphql/query" not in url:
            return

        try:
            body = await response.text()
        except PlaywrightError:
            return

        if MESSAGE_GRAPHQL_FRAGMENT not in body:
            return

        try:
            self._payloads.append(json.loads(body))
        except ValueError:
            return

    def _ingest(self, target):
        for payload in self._payloads[self._processed :]:
            self._processed += 1

            data = payload.get("data")

            if not isinstance(data, dict):
                continue

            for key in MESSAGE_PAYLOAD_KEYS:
                container = data.get(key)

                if not isinstance(container, dict):
                    continue

                thread = container.get("as_ig_direct_thread") or container.get(MESSAGE_GRAPHQL_FRAGMENT)

                if not isinstance(thread, dict):
                    continue

                self._found = True

                self._register_users(thread.get("users"))

                viewer = thread.get("viewer_id")

                if viewer is not None and self._viewer is None:
                    self._viewer = viewer

                slide = thread.get(MESSAGE_GRAPHQL_FRAGMENT)

                if not isinstance(slide, dict):
                    slide = thread if "edges" in thread else {}

                self._register_messages(slide, target)

        return self._messages

    def _register_users(self, users):
        for user in users or []:
            if not isinstance(user, dict) or not user.get("username"):
                continue

            for key in (user.get("id"), user.get("interop_messaging_user_fbid")):
                if key:
                    self._users[str(key)] = user["username"]

    def _register_messages(self, slide, target):
        for edge in slide.get("edges") or []:
            node = edge.get("node") if isinstance(edge, dict) else None

            if not isinstance(node, dict):
                continue

            message = self._message(node, self._users, self._viewer, target)

            if message and message not in self._messages:
                self._messages.append(message)

        page_info = slide.get("page_info") or {}

        if "has_next_page" in page_info:
            self._has_next = bool(page_info["has_next_page"])

    def _message(self, node, users, viewer, target):
        stamp = node.get("timestamp_ms") or node.get("timestamp")

        if not stamp:
            return None

        timestamp = self._unix_seconds(stamp)

        if timestamp is None:
            return None

        sender, is_self = self._sender(node, users, viewer)

        if is_self is None:
            is_self = bool(sender) and sender.lower() != target.lower()

        return {
            "timestamp": timestamp,
            "sender": sender,
            "isSelf": is_self,
            "content": self._content(node),
        }

    async def _scroll_history(self):
        point = await self._scroll_point()

        if point is None:
            return False

        await self._page.mouse.move(point[0], point[1])

        for _ in range(MESSAGE_SCROLL_STEPS):
            await self._page.mouse.wheel(0, -MESSAGE_SCROLL_DELTA)
            await asleep(MESSAGE_SLEEP_POLL)

        return True

    async def _scroll_point(self):
        composer = self._page.locator(", ".join(MESSAGE_SEL_COMPOSER_CANDIDATES)).first

        try:
            box = await composer.bounding_box(timeout=MESSAGE_TO_CHAT_WINDOW)
        except PlaywrightError:
            box = None

        if box is not None:
            return box["x"] + box["width"] / 2, max(box["y"] - MESSAGE_SCROLL_COMPOSER_GAP, 0)

        for selector in (MESSAGE_SEL_ARTICLE, MESSAGE_SEL_THREAD):
            target = self._page.locator(f"{selector}:visible").last

            try:
                box = await target.bounding_box(timeout=MESSAGE_TO_CHAT_WINDOW)
            except PlaywrightError:
                box = None

            if box is not None:
                return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2

        return None

    async def _wait_page(self, before):
        return await poll_for(lambda: len(self._payloads) > before, timeout_s=MESSAGE_TO_PAGE / 1000)

    async def _collect_history(self, target):
        if not self._payloads:
            await self._wait_page(0)

        messages = self._ingest(target)

        if not self._found:
            error("Aucune donnée de conversation reçue : sélecteur ou compte à revoir.")

            return None

        if not messages:
            return []

        return await self._paginate(messages, target)

    async def _paginate(self, messages, target):
        rounds = 0
        stable = 0

        while self._has_next:
            if rounds >= MESSAGE_HISTORY_ROUNDS:
                error(f"Historique incomplet : limite de {MESSAGE_HISTORY_ROUNDS} pages atteinte.")

                return None

            rounds += 1
            before = len(self._payloads)

            if not await self._scroll_history():
                error("Zone de défilement introuvable dans la fenêtre de messagerie.")

                return None

            if not await self._wait_page(before):
                error("La pagination de l'historique ne répond pas : blocage.")

                return None

            previous = len(messages)
            messages = self._ingest(target)

            if len(messages) == previous:
                stable += 1

                if stable >= MESSAGE_HISTORY_STABLE:
                    error("Historique incomplet : la pagination n'apporte plus de messages.")

                    return None
            else:
                stable = 0

        return sorted(messages, key=lambda m: m["timestamp"])

    async def _wait_sent(self, message):
        sent = await wait_dom(
            self._page,
            "sent_state",
            {
                "articleSelector": MESSAGE_SEL_ARTICLE,
                "composerSelector": ", ".join(MESSAGE_SEL_COMPOSER_CANDIDATES),
                "message": message,
            },
            timeout_ms=MESSAGE_SEND_POLL_MAX * MESSAGE_SLEEP_SEND_POLL * 1000,
        )

        if sent:
            return True

        error(f"L'envoi du message n'a pas été confirmé : {message[:40]}.")

        return False


__all__ = ["Message"]
