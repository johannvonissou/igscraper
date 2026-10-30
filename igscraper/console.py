import asyncio
import importlib
import json
import shlex
import sys
import time
from contextlib import suppress

from patchright.async_api import Error as PlaywrightError

from igscraper.browser import BrowserOptions
from igscraper.client import Instagram
from igscraper.constants import (
    CONSOLE_ALIASES,
    CONSOLE_DEFAULT_LAST,
    CONSOLE_HELP,
    CONSOLE_HELP_TEXT,
    CONSOLE_OFF_VALUES,
    CONSOLE_ON_VALUES,
    CONSOLE_PAIR,
    CONSOLE_PROMPT,
    CONSOLE_QUIT,
    CONSOLE_SESSION_PREVIEW,
)
from igscraper.errors import IGScraperError, summarize
from igscraper.render import paint, render

with suppress(ImportError):
    importlib.import_module("readline")


class ConsoleUsageError(ValueError):
    pass


def duration(seconds):
    if seconds < 1:
        return f"{seconds * 1000:.0f} ms"

    return f"{seconds:.2f} s"


def toggle(tokens, current):
    value = tokens[0].lower() if tokens else ""

    if value in CONSOLE_ON_VALUES:
        return True

    if value in CONSOLE_OFF_VALUES:
        return False

    if value:
        msg = "valeur attendue : on ou off"
        raise ConsoleUsageError(msg)

    return not current


def take_flag(tokens, flag):
    return flag in tokens, [token for token in tokens if token != flag]


def take_last(tokens, default=CONSOLE_DEFAULT_LAST):
    if "--last" not in tokens:
        return default, tokens

    index = tokens.index("--last")

    if index + 1 >= len(tokens):
        msg = "--last attend un nombre"
        raise ConsoleUsageError(msg)

    raw = tokens[index + 1]

    try:
        value = int(raw)
    except ValueError as exc:
        msg = f"--last attend un nombre entier (reçu : {raw})"
        raise ConsoleUsageError(msg) from exc

    if value < 0:
        msg = "--last doit être positif (0 = tout)"
        raise ConsoleUsageError(msg)

    return value, tokens[:index] + tokens[index + 2 :]


def usage(text):
    msg = f"usage : {text}"
    raise ConsoleUsageError(msg)


class Console:
    def __init__(self, options, *, sessionid=None, username=None, password=None, json_mode=False):
        self._options = options
        self._sessionid = sessionid
        self._username = username
        self._password = password
        self._json = json_mode
        self._client = None
        self._commands = {
            "login": self._login,
            "logout": self._logout,
            "search": self._search,
            "account": self._account,
            "follow": self._follow,
            "messages": self._messages,
            "send": self._send,
            "status": self._status,
            "headless": self._headless,
            "json": self._json_mode,
        }

    async def start(self):
        self._client = await Instagram(self._options).start()

        if self._sessionid:
            await self._timed("login", lambda: self._client.login(sessionid=self._sessionid), self._login_view)
        elif self._username and self._password:
            await self._timed(
                "login",
                lambda: self._client.login(username=self._username, password=self._password),
                self._login_view,
            )
        else:
            result = await self._client.login(reuse_only=True)

            if result:
                self._print(paint(f"✔ Session du profil persistant réutilisée ({self._session_label()}).", "green"))

        self._password = None

    async def close(self):
        if self._client is not None:
            await self._client.close()

        self._client = None

    async def run(self):
        self._print(paint("Console igscraper : « help » pour l'aide, « quit » pour sortir.", "bold"))

        if not self._client.logged_in:
            self._print(paint("Aucune session active : utilisez « login ».", "gray"))

        while True:
            try:
                line = await asyncio.to_thread(input, CONSOLE_PROMPT)
            except EOFError:
                self._print("")

                return
            except KeyboardInterrupt:
                self._print("")

                continue

            if not await self.handle(line):
                return

    async def handle(self, line):
        try:
            tokens = shlex.split(line)
        except ValueError as exc:
            self._error(f"ligne mal formée : {exc}")

            return True

        if not tokens:
            return True

        name = tokens[0].lower()
        name = CONSOLE_ALIASES.get(name, name)

        if name in CONSOLE_QUIT:
            return False

        if name in CONSOLE_HELP:
            self._print(CONSOLE_HELP_TEXT)

            return True

        command = self._commands.get(name)

        if command is None:
            self._error(f"commande inconnue : {name} (« help » pour l'aide)")

            return True

        once, rest = take_flag(tokens[1:], "--json")
        previous = self._json
        self._json = self._json or once

        try:
            await command(rest)
        except ConsoleUsageError as exc:
            self._error(str(exc))
        finally:
            if once:
                self._json = previous

        return True

    def _print(self, text):
        sys.stdout.write(f"{text}\n")
        sys.stdout.flush()

    def _error(self, text):
        self._print(paint(f"✘ {text}", "red"))

    def _elapsed(self, started):
        self._print(paint(f"⏱  {duration(time.perf_counter() - started)}", "cyan"))

    def _session_label(self):
        sessionid = (self._client.sessionid if self._client else None) or ""

        return f"{sessionid[:CONSOLE_SESSION_PREVIEW]}…, {len(sessionid)} caractères"

    def _emit(self, name, data, view):
        if self._json:
            self._print(json.dumps(data, ensure_ascii=False, indent=2, default=str))

            return

        self._print(view(data) if view is not None else render(name, data))

    async def _timed(self, name, factory, view=None):
        if self._client is None:
            self._error("navigateur indisponible : relancez-le avec « headless on|off ».")

            return

        self._print(paint(f"→ {name}…", "gray"))
        started = time.perf_counter()

        try:
            data = await factory()
        except IGScraperError as exc:
            self._error(str(exc))
        except PlaywrightError as exc:
            self._error(summarize(exc))
        else:
            self._emit(name, data, view)

        self._elapsed(started)

    def _login_view(self, result):
        if not result:
            return paint(f"✘ Connexion refusée : {result.reason or 'raison inconnue'}", "red")

        return render("login", {"sessionId": result.sessionid, "method": result.method})

    async def _login(self, tokens):
        if tokens[:1] in (["--sessionid"], ["-s"]):
            if len(tokens) != CONSOLE_PAIR:
                usage("login --sessionid <cookie>")

            sessionid = tokens[1]
            await self._timed("login", lambda: self._client.login(sessionid=sessionid), self._login_view)

            return

        if len(tokens) == CONSOLE_PAIR:
            username, password = tokens
            await self._timed(
                "login",
                lambda: self._client.login(username=username, password=password),
                self._login_view,
            )

            return

        if tokens:
            usage("login | login <utilisateur> <mot_de_passe> | login --sessionid <cookie>")

        await self._timed("login", self._client.login, self._login_view)

    async def _logout(self, tokens):
        if tokens:
            usage("logout")

        await self._timed("logout", self._client.logout, lambda _: render("logout", {}))

    async def _search(self, tokens):
        query = " ".join(tokens).strip()

        if not query:
            usage("search <texte>")

        await self._timed("search", lambda: self._client.search(query))

    async def _account(self, tokens):
        if len(tokens) != 1:
            usage("account <compte>")

        await self._timed("account", lambda: self._client.account(tokens[0]))

    async def _follow(self, tokens):
        if len(tokens) != 1:
            usage("follow <compte>")

        username = tokens[0]

        async def follow():
            await self._client.follow(username)

            return {"username": username.lstrip("@"), "followed": True}

        await self._timed("follow", follow)

    async def _messages(self, tokens):
        last, tokens = take_last(tokens)

        if len(tokens) != 1:
            usage("messages <compte> [--last N]")

        await self._timed(
            "messages",
            lambda: self._client.messages(tokens[0]),
            lambda data: render("messages", data, last),
        )

    async def _send(self, tokens):
        history, tokens = take_flag(tokens, "--history")
        last, tokens = take_last(tokens)

        if len(tokens) < CONSOLE_PAIR:
            usage("send <compte> <texte> [--history] [--last N]")

        username, text = tokens[0], " ".join(tokens[1:])

        await self._timed(
            "send",
            lambda: self._client.send_message(username, text, history=history),
            lambda data: render("send", data, last),
        )

    async def _status(self, tokens):
        if tokens:
            usage("status")

        running = self._client is not None
        logged = running and self._client.logged_in
        session = paint("connectée", "green") + f" ({self._session_label()})" if logged else "non connectée"

        self._print(f"navigateur : {paint('démarré', 'green') if running else 'arrêté'}")
        self._print(f"session    : {session}")
        self._print(f"headless   : {'on' if self._options.headless else 'off'}")
        self._print(f"médias     : {'bloqués' if self._options.block_media else 'chargés'}")
        self._print(f"json       : {'on' if self._json else 'off'}")

    async def _json_mode(self, tokens):
        self._json = toggle(tokens, self._json)
        self._print(f"json : {'on' if self._json else 'off'}")

    async def _headless(self, tokens):
        enabled = toggle(tokens, self._options.headless)

        if enabled == self._options.headless and self._client is not None:
            self._print(f"headless : {'on' if enabled else 'off'} (déjà actif)")

            return

        self._print(paint("→ redémarrage du navigateur…", "gray"))
        started = time.perf_counter()
        sessionid = self._client.sessionid if self._client is not None else None

        await self.close()
        self._options.headless = enabled

        try:
            self._client = await Instagram(self._options).start()

            if not sessionid or not await self._client.login(sessionid=sessionid):
                await self._client.login(reuse_only=True)
        except IGScraperError as exc:
            self._error(str(exc))
        else:
            self._print(f"headless : {'on' if enabled else 'off'} · navigateur relancé")

        self._elapsed(started)


async def serve(args):
    options = BrowserOptions(headless=not args.headed, block_media=not args.load_media)
    console = Console(
        options,
        sessionid=args.sessionid,
        username=args.username,
        password=args.password,
        json_mode=args.json,
    )

    try:
        await console.start()
        await console.run()
    except IGScraperError as exc:
        sys.stderr.write(paint(f"✘ {exc}", "red") + "\n")

        return 1
    finally:
        await console.close()

    return 0


__all__ = ["Console", "serve"]
