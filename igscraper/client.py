from contextlib import AsyncExitStack

from igscraper.account import Account
from igscraper.browser import BrowserOptions, first_page, stealth_browser
from igscraper.constants import BROWSER_NOT_STARTED
from igscraper.errors import BrowserError, LoginRequiredError, ScrapeError
from igscraper.login import Login
from igscraper.message import Message
from igscraper.search import Search


class Instagram:
    def __init__(self, options=None, *, manual_resolution=None):
        self._options = options or BrowserOptions()
        self._manual_resolution = (not self._options.headless) if manual_resolution is None else manual_resolution

        self._stack = None
        self._context = None
        self._page = None

        self._login = None
        self._search = None
        self._account = None
        self._message = None

        self._sessionid = None

    async def __aenter__(self):
        return await self.start()

    async def __aexit__(self, *_):
        await self.close()

    def __repr__(self):
        state = "connecté" if self.logged_in else "non connecté"
        running = "démarré" if self._context is not None else "arrêté"

        return f"<Instagram {running}, {state}>"

    async def start(self):
        if self._context is not None:
            return self

        stack = AsyncExitStack()

        try:
            context = await stack.enter_async_context(stealth_browser(self._options))
            page = await first_page(context)
        except BaseException:
            await stack.aclose()

            raise

        self._stack = stack
        self._context = context
        self._page = page

        self._login = Login(page, manual_resolution=self._manual_resolution)
        self._search = Search(page)
        self._account = Account(page)
        self._message = Message(page)

        return self

    async def close(self):
        if self._message is not None:
            await self._message.detach()

        if self._stack is not None:
            await self._stack.aclose()

        self._stack = None
        self._context = None
        self._page = None
        self._login = None
        self._search = None
        self._account = None
        self._message = None
        self._sessionid = None

    async def login(self, username=None, password=None, sessionid=None, *, reuse_only=False):
        await self.start()

        result = await self._service(self._login).login(
            username=username,
            password=password,
            sessionid=sessionid,
            reuse_only=reuse_only,
        )

        if result.success:
            self._sessionid = result.sessionid

        return result

    async def logout(self):
        await self.start()

        result = await self._service(self._login).logout()
        self._sessionid = None

        return result

    async def ensure_login(self):
        if self._sessionid:
            return self._sessionid

        result = await self.login(reuse_only=True)

        if not result.success or not result.sessionid:
            raise LoginRequiredError(result.reason or "session requise : appelez login() avec des identifiants.")

        return result.sessionid

    async def search(self, query):
        await self.ensure_login()

        results = await self._service(self._search).search(query)

        if results is None:
            msg = f"Recherche échouée pour « {query} »."
            raise ScrapeError(msg)

        return results

    async def account(self, username):
        await self.ensure_login()

        data = await self._service(self._account).retrieve(username)

        if data is None:
            msg = f"Profil @{Account.normalize_username(username)} inaccessible."
            raise ScrapeError(msg)

        return data

    async def follow(self, username):
        await self.ensure_login()

        followed = await self._service(self._account).follow(username)

        if not followed:
            msg = f"Abonnement à @{Account.normalize_username(username)} impossible."
            raise ScrapeError(msg)

        return True

    async def messages(self, username):
        await self.ensure_login()

        data = await self._service(self._message).get_messages(username)

        if not data:
            msg = f"Conversation avec @{Account.normalize_username(username)} inaccessible."
            raise ScrapeError(msg)

        return data

    async def send_message(self, username, message, *, history=False):
        await self.ensure_login()

        data = await self._service(self._message).send_message(username, message, history=history)

        if not data:
            msg = f"Envoi du message à @{Account.normalize_username(username)} échoué."
            raise ScrapeError(msg)

        return data

    disconnect = logout

    get_profile = account

    get_messages = messages

    send = send_message

    @property
    def page(self):
        if self._page is None:
            raise BrowserError(BROWSER_NOT_STARTED)

        return self._page

    @property
    def context(self):
        if self._context is None:
            raise BrowserError(BROWSER_NOT_STARTED)

        return self._context

    @property
    def sessionid(self):
        return self._sessionid

    @property
    def logged_in(self):
        return self._sessionid is not None

    def _service(self, service):
        if service is None:
            raise BrowserError(BROWSER_NOT_STARTED)

        return service


__all__ = ["Instagram"]
