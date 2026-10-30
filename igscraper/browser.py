import platform
import re
import subprocess
from contextlib import asynccontextmanager
from functools import cache
from pathlib import Path

from patchright.async_api import Error as PlaywrightError
from patchright.async_api import async_playwright

from igscraper.constants import (
    BROWSER_ARGS,
    BROWSER_CHROME_PATH,
    BROWSER_DEFAULTS,
    BROWSER_FALLBACK_GIF_CONTENT_TYPE,
    BROWSER_GPU_FLAGS,
    BROWSER_GPU_PATH,
    BROWSER_MEDIA_BLOCKED,
    BROWSER_MEDIA_GIF,
    BROWSER_MEDIA_PATTERNS,
    BROWSER_MEDIA_RESOURCE_TYPE,
    BROWSER_MEDIA_STATUS,
    BROWSER_PROFILE_DIR,
    BROWSER_WINDOW_HEIGHT,
    BROWSER_WINDOW_WIDTH,
    debug,
    info,
)
from igscraper.errors import BrowserError, summarize

USER_AGENT_TEMPLATES = {
    "Linux": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/{major}.0.0.0 Safari/537.36"
    ),
    "Darwin": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/{major}.0.0.0 Safari/537.36"
    ),
    "Windows": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/{major}.0.0.0 Safari/537.36"
    ),
}


class BrowserOptions:
    __slots__ = (
        "block_media",
        "extra_args",
        "headless",
        "locale",
        "slow_mo",
        "timezone_id",
        "user_agent",
        "user_data_dir",
    )

    def __init__(self, **values):
        unknown = values.keys() - BROWSER_DEFAULTS.keys()

        if unknown:
            names = ", ".join(sorted(unknown))
            msg = f"Options de navigateur inconnues : {names}"
            raise TypeError(msg)

        for name, default in BROWSER_DEFAULTS.items():
            setattr(self, name, values.get(name, default))


async def soft_block_media(route):
    resource_type = route.request.resource_type

    if resource_type not in BROWSER_MEDIA_BLOCKED:
        await route.fallback()

        return

    if resource_type == BROWSER_MEDIA_RESOURCE_TYPE:
        await route.abort()

        return

    await route.fulfill(
        status=BROWSER_MEDIA_STATUS,
        body=BROWSER_MEDIA_GIF,
        content_type=BROWSER_FALLBACK_GIF_CONTENT_TYPE,
    )


def resolve_profile_dir(user_data_dir=None):
    return Path(user_data_dir).expanduser() if user_data_dir else BROWSER_PROFILE_DIR


def _launch_kwargs():
    chosen = BROWSER_CHROME_PATH

    if not chosen.is_file():
        msg = f"Binaire Chromium local introuvable : {chosen}. Lancez « make build »."
        raise BrowserError(msg)

    debug(f"Chromium utilisé : {chosen}.")

    return {"executable_path": str(chosen)}


@cache
def chrome_major_version():
    try:
        result = subprocess.run(  # noqa: S603
            [str(BROWSER_CHROME_PATH), "--version"],
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    match = re.search(r"(\d+)\.", result.stdout or "")

    return match.group(1) if match else None


@cache
def headless_user_agent():
    major = chrome_major_version()

    if major is None:
        return None

    template = USER_AGENT_TEMPLATES.get(platform.system())

    return template.format(major=major) if template else None


def accept_language(locale):
    if not locale:
        return None

    base = locale.split("-")[0]

    return locale if base == locale else f"{locale},{base}"


def launch_args(config):
    size = f"{BROWSER_WINDOW_WIDTH},{BROWSER_WINDOW_HEIGHT}"
    args = [*BROWSER_ARGS, f"--window-size={size}"]

    if config.headless and platform.system() == "Linux":
        args.append(f"--ozone-override-screen-size={size}")

        if BROWSER_GPU_PATH.is_dir():
            args.extend(BROWSER_GPU_FLAGS)

    language = accept_language(config.locale)

    if language:
        args.append(f"--accept-lang={language}")

    return [*args, *(config.extra_args or ())]


def resolve_user_agent(config):
    if config.user_agent:
        return config.user_agent

    return headless_user_agent() if config.headless else None


@asynccontextmanager
async def stealth_browser(options=None):
    config = options or BrowserOptions()

    profile = resolve_profile_dir(config.user_data_dir)
    profile.mkdir(parents=True, exist_ok=True)

    launch_options = {
        "headless": config.headless,
        "no_viewport": True,
        "locale": config.locale,
        "timezone_id": config.timezone_id,
        "args": launch_args(config),
    }

    user_agent = resolve_user_agent(config)

    if user_agent:
        launch_options["user_agent"] = user_agent

    if config.slow_mo is not None:
        launch_options["slow_mo"] = config.slow_mo

    async with async_playwright() as playwright:
        try:
            context = await playwright.chromium.launch_persistent_context(
                user_data_dir=str(profile),
                **_launch_kwargs(),
                **launch_options,
            )
        except PlaywrightError as exc:
            msg = f"Impossible de lancer Chromium ({summarize(exc)}). Installez Chrome ou lancez « make build »."
            raise BrowserError(msg) from exc

        if config.block_media:
            for pattern in BROWSER_MEDIA_PATTERNS:
                await context.route(pattern, soft_block_media)

        info(f"Navigateur prêt (headless={config.headless}, profil={profile}).")

        try:
            yield context
        finally:
            try:
                await context.close()
            except PlaywrightError as exc:
                debug(f"Fermeture du navigateur ignorée : {summarize(exc)}")


async def first_page(context):
    if context.pages:
        return context.pages[0]

    return await context.new_page()


__all__ = [
    "BrowserOptions",
    "first_page",
    "resolve_profile_dir",
    "soft_block_media",
    "stealth_browser",
]
