import re
import time

from patchright.async_api import Error as PlaywrightError
from patchright.async_api import TimeoutError as PlaywrightTimeoutError

from igscraper.constants import (
    GLOBAL_SLEEP_WRITE,
    LOGIN_BTN_NAME_PATTERN,
    LOGIN_CHALLENGES,
    LOGIN_COOKIE_DOMAIN,
    LOGIN_COOKIE_PATH,
    LOGIN_COOKIE_SESSIONID,
    LOGIN_COOKIE_VERIFICATION,
    LOGIN_PASSWORD_ALERT_DELAY,
    LOGIN_PENDING,
    LOGIN_SEL_ALERT,
    LOGIN_SEL_COOKIES_CANDIDATES,
    LOGIN_SEL_CREDENTIAL_INPUT,
    LOGIN_SEL_EMAIL_INPUT,
    LOGIN_SEL_LATER_CANDIDATES,
    LOGIN_SEL_LOGIN_BTN_CANDIDATES,
    LOGIN_SEL_LOGIN_FORM,
    LOGIN_SEL_SAVE_LOGIN_CANDIDATES,
    LOGIN_SLEEP_INTER,
    LOGIN_SLEEP_MANUAL_POLL,
    LOGIN_SLEEP_POLL,
    LOGIN_SLEEP_POLL_OUTCOME,
    LOGIN_TO_ATTRIBUTE,
    LOGIN_TO_COOKIES,
    LOGIN_TO_LATER,
    LOGIN_TO_LOGIN_BTN,
    LOGIN_TO_LOGIN_FORM,
    LOGIN_TO_MANUAL,
    LOGIN_TO_SAVE_LOGIN,
    LOGIN_URL_CHALLENGE,
    LOGIN_URL_RECAPTCHA,
    MAIN_PAGE,
    asleep,
    error,
    info,
    success,
    warn,
)
from igscraper.errors import summarize
from igscraper.navigation import click_first, goto_page, is_present


class LoginMethod:
    COOKIE = "cookie"
    CREDENTIALS = "password"
    SESSIONID = "sessionid"


class LoginResult:
    __slots__ = ("challenge", "method", "reason", "sessionid", "success")

    def __init__(self, success, method=None, sessionid=None, reason=None, challenge=None):
        self.success = success
        self.method = method
        self.sessionid = sessionid
        self.reason = reason
        self.challenge = challenge

    def __bool__(self):
        return self.success

    def __str__(self):
        if self.success:
            length = len(self.sessionid or "")

            return f"connexion réussie via {self._method_label} (sessionid de {length} caractères)"

        return f"connexion échouée via {self._method_label} : {self.reason}"

    @property
    def _method_label(self):
        return self.method or "inconnue"


class Login:
    def __init__(self, page, *, manual_resolution=True, manual_timeout=LOGIN_TO_MANUAL):
        self._page = page
        self._manual_resolution = manual_resolution
        self._manual_timeout = manual_timeout

    async def login(self, username=None, password=None, sessionid=None, *, reuse_only=False):
        method = self._resolve_method(username, password, sessionid, reuse_only=reuse_only)

        if method is None:
            return self._fail(None, "identifiants incomplets : fournissez sessionid, ou username + password")

        try:
            return await self._run(method, username, password, sessionid)
        except PlaywrightError as exc:
            return self._fail(method, summarize(exc))

    async def is_authenticated(self):
        return await self._is_authenticated()

    async def login_recover(self, username, password):
        result = await self.login(username=username, password=password)

        return result.sessionid

    async def login_classic(self, username, password):
        result = await self.login(username=username, password=password)

        return result.success

    async def login_sessionid(self, sessionid):
        result = await self.login(sessionid=sessionid)

        return result.success

    async def logout(self):
        await self._page.context.clear_cookies()
        success("Déconnexion réussie (cookies effacés).")
        return LoginResult(success=True, method="logout")

    disconnect = logout

    def _resolve_method(self, username, password, sessionid, *, reuse_only):
        if reuse_only:
            return LoginMethod.COOKIE

        if sessionid:
            return LoginMethod.SESSIONID

        if username and password:
            return LoginMethod.CREDENTIALS

        if username or password:
            return None

        return LoginMethod.COOKIE

    async def _run(self, method, username, password, sessionid):
        await self._open_home()
        await self._accept_cookies()

        if await self._is_authenticated():
            info("Profil déjà authentifié : réutilisation de la session existante.")

            return await self._finish(method)

        failure = await self._attempt(method, username, password, sessionid)

        if failure is not None:
            return failure

        failure = await self._await_outcome(method)

        if failure is not None:
            return failure

        await self._dismiss_popups(method)

        return await self._finish(method)

    async def _attempt(self, method, username, password, sessionid):
        if method is LoginMethod.COOKIE:
            return self._fail(method, "aucune session active dans ce profil")

        if method is LoginMethod.SESSIONID:
            if not sessionid:
                return self._fail(method, "sessionid manquant")

            await self._inject_sessionid(sessionid)
            await self._open_home()

            return None

        if not await self._fill_credentials(username or "", password or ""):
            return self._fail(method, "formulaire de connexion introuvable")

        if not await self._submit():
            return self._fail(method, "bouton de connexion indisponible")

        return None

    async def _open_home(self):
        await goto_page(self._page, MAIN_PAGE)

        try:
            title = await self._page.title()
        except PlaywrightError:
            title = ""

        info(f"Page ouverte : {title or MAIN_PAGE}.")

    async def _accept_cookies(self):
        await click_first(
            self._page,
            LOGIN_SEL_COOKIES_CANDIDATES,
            timeout_ms=LOGIN_TO_COOKIES,
            label="Bannière de cookies",
        )

    async def _inject_sessionid(self, sessionid):
        await self._page.context.add_cookies(
            [
                {
                    "name": LOGIN_COOKIE_SESSIONID,
                    "value": sessionid,
                    "domain": LOGIN_COOKIE_DOMAIN,
                    "path": LOGIN_COOKIE_PATH,
                    "secure": True,
                    "httpOnly": True,
                    "sameSite": "Lax",
                },
            ],
        )

        info(f"Cookie sessionid injecté ({len(sessionid)} caractères).")

    async def _fill_credentials(self, username, password):
        email = self._page.locator(LOGIN_SEL_EMAIL_INPUT).first
        credential = self._page.locator(LOGIN_SEL_CREDENTIAL_INPUT).first

        try:
            await email.wait_for(state="visible", timeout=LOGIN_TO_LOGIN_FORM)
            await credential.wait_for(state="visible", timeout=LOGIN_TO_LOGIN_FORM)
        except PlaywrightTimeoutError:
            error(f"Champs de connexion introuvables ('{LOGIN_SEL_EMAIL_INPUT}', '{LOGIN_SEL_CREDENTIAL_INPUT}').")

            return False

        await email.fill("")
        await email.press_sequentially(username, delay=GLOBAL_SLEEP_WRITE)

        await credential.fill("")
        await credential.press_sequentially(password, delay=GLOBAL_SLEEP_WRITE)

        return True

    async def _submit(self):
        button = await self._find_submit_button()

        if button is None:
            error("Bouton « Se connecter » introuvable.")

            return False

        if not await self._wait_enabled(button):
            error("Bouton « Se connecter » resté désactivé.")

            return False

        await button.click(timeout=LOGIN_TO_LOGIN_FORM)

        info("Bouton « Se connecter » cliqué.")

        return True

    async def _find_submit_button(self):
        for selector in LOGIN_SEL_LOGIN_BTN_CANDIDATES:
            locator = self._page.locator(selector)

            if await locator.count():
                return locator.first

        form = self._page.locator(LOGIN_SEL_LOGIN_FORM)

        if await form.count():
            named = form.get_by_role("button", name=re.compile(LOGIN_BTN_NAME_PATTERN, re.IGNORECASE))

            if await named.count():
                return named.first

        return None

    async def _wait_enabled(self, button, timeout_ms=LOGIN_TO_LOGIN_BTN):
        deadline = time.monotonic() + timeout_ms / 1000

        while time.monotonic() < deadline:
            try:
                disabled = (await button.get_attribute("aria-disabled", timeout=LOGIN_TO_ATTRIBUTE)) == "true"
                enabled = await button.is_enabled(timeout=LOGIN_TO_ATTRIBUTE)
            except PlaywrightError:
                return False

            if not disabled and enabled:
                return True

            await asleep(LOGIN_SLEEP_POLL)

        return False

    async def _await_outcome(self, method):
        deadline = time.monotonic() + LOGIN_TO_LOGIN_FORM / 1000
        started = time.monotonic()

        while time.monotonic() < deadline:
            outcome = await self._poll_outcome(method, started)

            if outcome is not LOGIN_PENDING:
                return outcome

            await asleep(LOGIN_SLEEP_POLL_OUTCOME)

        return await self._final_outcome(method)

    async def _poll_outcome(self, method, started):
        challenge = await self._detect_challenge()

        if challenge:
            info(f"Challenge détecté : {challenge}.")

            if await self._resolve_challenge(challenge):
                return None

            return self._fail(method, "challenge non résolu", challenge)

        if await self._is_authenticated():
            return None

        if method is LoginMethod.SESSIONID and await is_present(self._page, LOGIN_SEL_LOGIN_FORM):
            return await self._sessionid_outcome(method)

        if method is LoginMethod.CREDENTIALS and time.monotonic() - started > LOGIN_PASSWORD_ALERT_DELAY:
            alert = await self._alert()

            if alert:
                return self._fail(method, f"refusé par Instagram : {alert}")

        return LOGIN_PENDING

    async def _sessionid_outcome(self, method):
        await asleep(LOGIN_SLEEP_INTER / 3)

        if await self._is_authenticated():
            return None

        return self._fail(method, "sessionid invalide ou expiré")

    async def _final_outcome(self, method):
        challenge = await self._detect_challenge()

        if challenge:
            if await self._resolve_challenge(challenge):
                return None

            return self._fail(method, "challenge non résolu", challenge)

        alert = await self._alert()
        detail = f" : {alert}" if alert else ""

        return self._fail(method, f"délai de connexion dépassé{detail}")

    async def _dismiss_popups(self, method):
        if method is LoginMethod.CREDENTIALS:
            await click_first(
                self._page,
                LOGIN_SEL_SAVE_LOGIN_CANDIDATES,
                timeout_ms=LOGIN_TO_SAVE_LOGIN,
                label="Popup d'enregistrement des identifiants",
            )

            await asleep(LOGIN_SLEEP_INTER)

        await click_first(
            self._page,
            LOGIN_SEL_LATER_CANDIDATES,
            timeout_ms=LOGIN_TO_LATER,
            label="Popup de notifications",
        )

    async def _finish(self, method):
        cookies = await self._cookies()
        sessionid = cookies.get(LOGIN_COOKIE_SESSIONID)

        if not sessionid or LOGIN_COOKIE_VERIFICATION not in cookies:
            challenge = await self._detect_challenge()

            return self._fail(method, "session incomplète (cookies manquants)", challenge)

        if await is_present(self._page, LOGIN_SEL_EMAIL_INPUT):
            return self._fail(method, "formulaire de connexion encore affiché")

        success(f"Connexion réussie via {method} (sessionid de {len(sessionid)} caractères).")

        return LoginResult(success=True, method=method, sessionid=sessionid)

    async def _cookies(self):
        cookies = await self._page.context.cookies(MAIN_PAGE)

        return {cookie["name"]: cookie["value"] for cookie in cookies}

    async def _is_authenticated(self):
        url = self._page.url

        if LOGIN_URL_CHALLENGE in url or LOGIN_URL_RECAPTCHA in url:
            return False

        cookies = await self._cookies()

        if LOGIN_COOKIE_SESSIONID not in cookies:
            return False

        if LOGIN_COOKIE_VERIFICATION not in cookies:
            return False

        return not await is_present(self._page, LOGIN_SEL_EMAIL_INPUT)

    async def _detect_challenge(self):
        url = self._page.url

        if LOGIN_URL_CHALLENGE in url:
            return "checkpoint (/challenge)"

        if LOGIN_URL_RECAPTCHA in url:
            return "captcha (auth_platform/recaptcha)"

        for selector, label in LOGIN_CHALLENGES:
            if await is_present(self._page, selector):
                return label

        return None

    async def _alert(self):
        alert = self._page.locator(LOGIN_SEL_ALERT).first

        if not await alert.count():
            return None

        try:
            return (await alert.inner_text(timeout=LOGIN_TO_ATTRIBUTE)).strip() or None
        except PlaywrightError:
            return None

    async def _resolve_challenge(self, challenge=None):
        if not self._manual_resolution:
            error(
                "Challenge détecté mais la résolution manuelle est désactivée "
                "(mode headless). Relancez avec headless=False ou --headed",
            )

            return False

        timeout = self._manual_timeout
        info(
            (challenge or "Vérification")
            + f" : résolvez-le dans la fenêtre du navigateur (délai maximal : {timeout // 60} min).",
        )

        deadline = time.monotonic() + timeout
        announced = None

        while time.monotonic() < deadline:
            reason = await self._detect_challenge()
            alert = await self._alert()

            if reason is None and alert:
                reason = f"erreur signalée : {alert[:120]}"

            if reason != announced:
                warn(f"Blocage : {reason}." if reason else "Blocage levé.")

                announced = reason

            if reason is None and await self._is_authenticated():
                success("Challenge résolu manuellement.")

                return True

            await asleep(LOGIN_SLEEP_MANUAL_POLL)

        error("Challenge non résolu dans le délai imparti.")

        return False

    def _fail(self, method, reason, challenge=None):
        label = method or "inconnue"
        error(f"Connexion via {label} échouée : {reason}.")

        return LoginResult(success=False, method=method, reason=reason, challenge=challenge)


__all__ = ["Login", "LoginMethod", "LoginResult"]
