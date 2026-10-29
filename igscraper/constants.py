import asyncio
import logging
import re
import sys
from base64 import b64decode
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

MAIN_PAGE = "https://www.instagram.com"
SEARCH_PAGE = f"{MAIN_PAGE}/explore/"

BROWSER_CHROME_PATH = (PROJECT_ROOT / "vendor" / "chrome" / "chrome").expanduser()
BROWSER_PROFILE_DIR = PROJECT_ROOT / ".chrome-profile"

BROWSER_LOCALE = "fr-FR"
BROWSER_TIMEZONE = "Europe/Paris"

BROWSER_DEFAULTS = {
    "block_media": True,
    "extra_args": None,
    "headless": True,
    "locale": BROWSER_LOCALE,
    "slow_mo": None,
    "timezone_id": BROWSER_TIMEZONE,
    "user_data_dir": None,
}

BROWSER_NOT_STARTED = "Navigateur non démarré : utilisez « async with » ou await start()."

BROWSER_ARGS = (
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-blink-features=AutomationControlled",
)

BROWSER_MEDIA_BLOCKED = frozenset({"image", "media"})
BROWSER_MEDIA_RESOURCE_TYPE = "media"
BROWSER_MEDIA_STATUS = 200

BROWSER_MEDIA_GIF = b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")

BROWSER_FALLBACK_GIF_CONTENT_TYPE = "image/gif"
BROWSER_FALLBACK_MEDIA_CONTENT_TYPE = "video/mp4"

GLOBAL_SLEEP_WRITE = 40

NAVIGATION_TO_CLICK = 3000
NAVIGATION_SLEEP_RETRY = 1

RENDER_EMPTY = "—"
RENDER_LABEL_WIDTH = 14
RENDER_PLURAL_MIN = 2
RENDER_TIMESTAMP_FORMAT = "%d/%m/%Y à %H:%M:%S"

RENDER_ANSI = re.compile(r"\033\[[0-9;]*m")
RENDER_ZERO_WIDTH = frozenset("\u200b\u200c\u200d\ufe0e\ufe0f")
RENDER_EMOJI_START = 0x1F300

RENDER_STYLES = {
    "bold": "1",
    "dim": "2",
    "red": "31",
    "green": "32",
    "yellow": "33",
    "cyan": "36",
    "gray": "90",
}

RENDER_TERM_MIN = 50
RENDER_TERM_MAX = 100
RENDER_TERM_DEFAULT = 88
RENDER_BUBBLE_MIN_TEXT = 24
RENDER_BUBBLE_MAX_TEXT = 64
RENDER_SEND_DEFAULT_LAST = 10
RENDER_POST_DESCRIPTION_LINES = 2

RENDER_PAGED_COMMANDS = frozenset({"messages", "send"})

RENDER_DAYS = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")
RENDER_MONTHS = (
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
)

LOGIN_METHOD_COOKIE = "cookie"
LOGIN_METHOD_CREDENTIALS = "password"
LOGIN_METHOD_SESSIONID = "sessionid"

RENDERER_NAMES = {
    "login": "_render_login",
    "logout": "_render_logout",
    "disconnect": "_render_logout",
    "search": "_render_search",
    "account": "_render_account",
    "follow": "_render_follow",
    "messages": "_render_messages",
    "send": "_render_send",
}

ERROR_MAX_DETAIL = 160

LOGIN_SEL_EMAIL_INPUT = 'input[name="email"]'
LOGIN_SEL_CREDENTIAL_INPUT = 'input[name="pass"]'
LOGIN_SEL_LOGIN_FORM = "form#login_form"
LOGIN_SEL_LOGIN_BTN = 'form#login_form div[role="button"][aria-label="Se connecter"]'

LOGIN_SEL_LOGIN_BTN_CANDIDATES = (
    'form#login_form button[type="submit"]',
    LOGIN_SEL_LOGIN_BTN,
    'form#login_form div[role="button"][aria-label="Log in"]',
)

LOGIN_BTN_NAME_PATTERN = r"Se connecter|Connexion|Log ?in"

LOGIN_SEL_COOKIES_CANDIDATES = (
    'button:has-text("Autoriser tous les cookies")',
    'button:has-text("Tout autoriser")',
    'button:has-text("Allow all cookies")',
    'button:has-text("Accept all")',
)

LOGIN_SEL_SAVE_LOGIN_CANDIDATES = (
    'button:has-text("Enregistrer les identifiants")',
    'button:has-text("Enregistrer les informations")',
    'button:has-text("Save login info")',
    'button:has-text("Save info")',
)

LOGIN_SEL_LATER_CANDIDATES = (
    'button:has-text("Plus tard")',
    'button:has-text("Pas maintenant")',
    'button:has-text("Not now")',
    'div[role="button"]:has-text("Plus tard")',
    'div[role="button"]:has-text("Not now")',
)

LOGIN_SEL_CAPTCHA = 'iframe[src*="arkoselabs"]'
LOGIN_SEL_RECAPTCHA_IFRAME = "iframe#captcha-recaptcha"
LOGIN_SEL_TWOFACTOR_CODE = 'input[name="verificationCode"]'
LOGIN_TEXT_TWOFACTOR = "Vérification en deux étapes"
LOGIN_TEXT_SUSPICIOUS = "Nous avons détecté une activité inhabituelle"
LOGIN_SEL_ALERT = 'div[role="alert"]'

LOGIN_CHALLENGES = (
    (LOGIN_SEL_RECAPTCHA_IFRAME, "captcha reCAPTCHA (auth_platform)"),
    (LOGIN_SEL_CAPTCHA, "captcha (FunCaptcha/arkose)"),
    (LOGIN_SEL_TWOFACTOR_CODE, "code 2FA"),
    (f"text={LOGIN_TEXT_TWOFACTOR}", "vérification à deux facteurs"),
    (f"text={LOGIN_TEXT_SUSPICIOUS}", "activité inhabituelle"),
)

LOGIN_COOKIE_SESSIONID = "sessionid"
LOGIN_COOKIE_VERIFICATION = "ds_user_id"
LOGIN_COOKIE_DOMAIN = ".instagram.com"
LOGIN_COOKIE_PATH = "/"

LOGIN_URL_CHALLENGE = "/challenge"
LOGIN_URL_RECAPTCHA = "/auth_platform"

LOGIN_TO_COOKIES = 2000
LOGIN_TO_LOGIN_BTN = 1000
LOGIN_TO_LOGIN_FORM = 10000
LOGIN_TO_SAVE_LOGIN = 2000
LOGIN_TO_LATER = 2000
LOGIN_TO_ATTRIBUTE = 1000

LOGIN_SLEEP_INTER = 3
LOGIN_SLEEP_POLL = 0.2
LOGIN_SLEEP_POLL_OUTCOME = 0.5
LOGIN_PASSWORD_ALERT_DELAY = 2

LOGIN_TO_MANUAL = 300
LOGIN_SLEEP_MANUAL_POLL = 2

LOGIN_PENDING = object()

SESSION_DEFAULTS = {
    "headless": False,
    "manual_timeout": LOGIN_TO_MANUAL,
    "profile_dir": None,
    "verify": True,
}

SESSION_SLEEP_RESTART = 10

SEARCH_RESULTS_IMG_TEXT = "Photo de profil de "
SEARCH_SEL_RESULTS_IMG = f'img[alt^="{SEARCH_RESULTS_IMG_TEXT}"]'
SEARCH_SEL_RESULTS_CONTAINER = 'xpath=ancestor::div[.//span[@dir="auto"]][1]'
SEARCH_SEL_RESULTS_NAMES = 'span[dir="auto"]'
SEARCH_SEL_RESULTS_URL = "a[href]"

SEARCH_SEL_INPUT = 'input[aria-label="Saisie de la recherche"]'
SEARCH_SEL_INPUT_CANDIDATES = (
    SEARCH_SEL_INPUT,
    'input[placeholder="Rechercher"]',
    'input[aria-label="Search input"]',
)

SEARCH_SLEEP_INTER = 1
SEARCH_TO_RESULTS = 8000

ACCOUNT_SEL_HEADER = "main header"
ACCOUNT_SEL_USERNAME = "main header h2"
ACCOUNT_SEL_ADDRESS = "main header h1"
ACCOUNT_SEL_SECTION = "main header section"
ACCOUNT_SEL_BIO = 'main header div[role="button"]:has(span[dir="auto"]):not(:has(svg))'
ACCOUNT_SEL_BIO_LINK = 'main header a[href^="http"]'
ACCOUNT_SEL_FOLLOWERS = "main header span[title]"
ACCOUNT_SEL_POSTS = 'main a[href*="/p/"], main a[href*="/reel/"], main a[href*="/tv/"]'
ACCOUNT_SEL_BUTTONS = 'main button, main div[role="button"]'

ACCOUNT_POSTS_TEXT = "publications"
ACCOUNT_FOLLOWERS_TEXT = "followers"
ACCOUNT_FOLLOWING_TEXT = "suivi(e)s"
ACCOUNT_STATS_SUFFIXES = (
    ACCOUNT_POSTS_TEXT,
    ACCOUNT_FOLLOWERS_TEXT,
    ACCOUNT_FOLLOWING_TEXT,
)

ACCOUNT_PRIVATE_TEXT = "Ce profil est privé"
ACCOUNT_NAME_LINE_INDEX = 1
ACCOUNT_FOLLOWED_TEXT = "Suivi(e)"
ACCOUNT_OWN_TEXT = "Modifier le profil"
ACCOUNT_BIO_MORE_TEXT = "plus"

ACCOUNT_FOLLOW_TEXTS = ("Suivre", "S'abonner", "Follow")
ACCOUNT_REQUESTED_TEXT = "Demandé"
ACCOUNT_REQUESTED_CANCEL_TEXT = "Annuler la demande"

ACCOUNT_TO_PROFILE = 10000
ACCOUNT_TO_FOLLOW_CLICK = 5000
ACCOUNT_TO_BIO_CLICK = 3000
ACCOUNT_TO_ATTRIBUTE = 1000
ACCOUNT_TO_FOLLOW = 10
ACCOUNT_SLEEP_INTER = 2

MESSAGE_CONTACT_TEXTS = ("Contacter", "Message")

MESSAGE_SEL_BUTTONS = 'main button, main div[role="button"]'
MESSAGE_SEL_COMPOSER = 'div[aria-placeholder="Votre message…"]'
MESSAGE_SEL_COMPOSER_CANDIDATES = (
    MESSAGE_SEL_COMPOSER,
    'div[aria-placeholder="Message..."]',
    'div[contenteditable="true"][role="textbox"]',
)
MESSAGE_SEL_ARTICLE = 'div[role="article"][aria-roledescription="message"]'
MESSAGE_SEL_THREAD = 'div[role="grid"]'

MESSAGE_SEL_CLOSE_CANDIDATES = (
    'div[role="button"][aria-label="Fermer"]',
    'div[role="button"][aria-label="Close"]',
    'button[aria-label="Fermer"]',
    'button[aria-label="Close"]',
)

MESSAGE_PAYLOAD_KEYS = ("get_slide_thread_nullable", "fetch__SlideThread")
MESSAGE_GRAPHQL_FRAGMENT = "slide_messages"

MESSAGE_CONTENT_PLACEHOLDERS = {
    "IMAGES": "<photo>",
    "VIDEO": "<vidéo>",
    "AUDIOS": "<vocal>",
    "VOICE_MEDIA": "<vocal>",
    "RAVEN_IMAGE": "<photo>",
    "RAVEN_VIDEO": "<vidéo>",
    "ANIMATED_MEDIA": "<sticker>",
    "STORY_SHARE": "<story>",
    "STORY_REPLY": "<story>",
    "REEL_SHARE": "<reel>",
    "CLIPS_SHARE": "<reel>",
    "XMA": "<média>",
}

MESSAGE_MEDIA_PLACEHOLDER = "<média>"

MESSAGE_TO_CHAT_WINDOW = 5000
MESSAGE_TO_PAGE = 8000

MESSAGE_TIMESTAMP_MICROSECONDS = 1_000_000_000_000_000
MESSAGE_TIMESTAMP_MILLISECONDS = 100_000_000_000

MESSAGE_SLEEP_WINDOW = 1
MESSAGE_SLEEP_POLL = 0.2
MESSAGE_SLEEP_SEND_POLL = 0.3

MESSAGE_SCROLL_DELTA = 1200
MESSAGE_SCROLL_STEPS = 4
MESSAGE_SCROLL_COMPOSER_GAP = 80

MESSAGE_HISTORY_ROUNDS = 40
MESSAGE_HISTORY_STABLE = 2
MESSAGE_SEND_POLL_MAX = 20

LOGGER_NAME = "igscraper"

SUCCESS = 25
logging.addLevelName(SUCCESS, "SUCCESS")

logger = logging.getLogger(LOGGER_NAME)
logger.addHandler(logging.NullHandler())

_RESET = "\033[0m"

_LEVEL_STYLES = {
    logging.DEBUG: ("\033[90m", "·"),
    logging.INFO: ("\033[90m", "◆"),
    SUCCESS: ("\033[92m", "✔"),
    logging.WARNING: ("\033[93m", "⚠"),
    logging.ERROR: ("\033[91m", "✘"),
}


class _ConsoleFormatter(logging.Formatter):
    def __init__(self, use_color):
        super().__init__("%(message)s")
        self._use_color = use_color

    def format(self, record):
        color, icon = _LEVEL_STYLES.get(record.levelno, ("", "•"))
        message = record.getMessage()

        if self._use_color and color:
            return f"{color}{icon} {message}{_RESET}"

        return f"{icon} {message}"


def configure_logging(level=None, color=None, *, quiet=False):
    logging.disable(logging.CRITICAL if quiet else logging.NOTSET)
    logger.disabled = quiet

    if quiet:
        return logger

    level = level or "INFO"

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(_ConsoleFormatter(sys.stderr.isatty() if color is None else color))

    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(level.upper() if isinstance(level, str) else level)
    logger.propagate = False

    return logger


def success(text):
    logger.log(SUCCESS, text)


def error(text):
    logger.error(text)


def warn(text):
    logger.warning(text)


def info(text):
    logger.info(text)


def debug(text):
    logger.debug(text)


async def asleep(seconds):
    await asyncio.sleep(seconds)
