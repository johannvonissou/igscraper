from patchright.async_api import Error as PlaywrightError

from igscraper.browser import BrowserOptions, first_page, stealth_browser
from igscraper.constants import SESSION_DEFAULTS, error, info, success, warn
from igscraper.errors import BrowserError, LoginError, summarize
from igscraper.login import Login, LoginResult


class SessionOptions:
    __slots__ = ("headless", "manual_timeout", "profile_dir", "verify")

    def __init__(self, **values):
        unknown = values.keys() - SESSION_DEFAULTS.keys()

        if unknown:
            names = ", ".join(sorted(unknown))
            msg = f"Options de session inconnues : {names}"
            raise TypeError(msg)

        for name, default in SESSION_DEFAULTS.items():
            setattr(self, name, values.get(name, default))


def _credentials(username, password):
    username = (username or "").strip()
    password = password or ""

    if bool(username) != bool(password):
        warn("Identifiants incomplets : fournissez username et password ensemble.")

    return username, password


async def _login(username, password, options):
    browser = BrowserOptions(
        user_data_dir=options.profile_dir,
        headless=options.headless,
        block_media=options.headless,
    )

    async with stealth_browser(browser) as context:
        page = await first_page(context)

        return await Login(
            page,
            manual_resolution=not options.headless,
            manual_timeout=options.manual_timeout,
        ).login(username=username, password=password)


async def _verify(sessionid, options):
    browser = BrowserOptions(
        user_data_dir=options.profile_dir,
        headless=True,
    )

    async with stealth_browser(browser) as context:
        page = await first_page(context)

        result = await Login(page, manual_resolution=False).login(sessionid=sessionid)

        if not result:
            warn(f"Vérification headless échouée : {result.reason}.")

        return result.success


async def _attempt(username, password, options):
    try:
        return await _login(username, password, options)
    except LoginError:
        raise
    except (BrowserError, PlaywrightError, OSError) as exc:
        reason = summarize(exc)
        error(f"Connexion interrompue : {reason}.")

        return LoginResult(success=False, reason=reason)


async def _verified_session(result, options):
    if not result or not result.sessionid:
        return False

    if not options.verify:
        success("Session obtenue.")

        return True

    try:
        verified = await _verify(result.sessionid, options)
    except (BrowserError, PlaywrightError, OSError) as exc:
        warn(f"Vérification headless interrompue : {summarize(exc)}.")
        verified = False

    if verified:
        success("Session opérationnelle en headless.")

        return True

    return False


async def establish_session_result(username=None, password=None, options=None):
    config = options or SessionOptions()
    username, password = _credentials(username, password)

    has_credentials = bool(username and password)

    if not has_credentials:
        info("Aucun identifiant fourni : réutilisation du profil persistant.")

    target = f"@{username}" if username else "profil persistant"
    info(f"Connexion au {target}.")

    result = await _attempt(username, password, config)

    if await _verified_session(result, config):
        return result

    error("Impossible d'établir une session valide.")

    if not has_credentials:
        error("Aucune session dans le profil. Passez username et password.")

    return None


async def establish_session(username=None, password=None, options=None):
    result = await establish_session_result(username, password, options)

    return result.sessionid if result else None


get_sessionid = establish_session


__all__ = ["SessionOptions", "establish_session", "establish_session_result", "get_sessionid"]
