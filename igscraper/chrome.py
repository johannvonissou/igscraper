import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from igscraper.constants import (
    BROWSER_CHROME_DEB_URL,
    BROWSER_CHROME_DIR,
    BROWSER_CHROME_PATH,
    BROWSER_PROFILE_DIR,
    BROWSER_VENDOR_DIR,
    PROJECT_ROOT,
    debug,
    info,
)
from igscraper.errors import BrowserError, summarize

AR_MAGIC = b"!<arch>\n"
AR_HEADER_SIZE = 60
AR_NAME_SIZE = 16
AR_SIZE_OFFSET = 48
AR_SIZE_LENGTH = 10
AR_MAGIC_OFFSET = 58

CHROME_DEB_MEMBER = "data.tar"
CHROME_TREE = ("opt", "google", "chrome")
CHROME_BINARY = "chrome"
CHROME_STAGING = ".chrome-new"

DOWNLOAD_BLOCK = 1 << 20
DOWNLOAD_TIMEOUT = 60
PROGRESS_STEP = 10
VERSION_TIMEOUT = 10

SIZE_UNITS = ("o", "Ko", "Mo", "Go", "To")
SIZE_BASE = 1024


def chrome_installed():
    return BROWSER_CHROME_PATH.is_file()


def chrome_version(path=BROWSER_CHROME_PATH):
    try:
        result = subprocess.run(  # noqa: S603
            [str(path), "--version"],
            capture_output=True,
            check=False,
            text=True,
            timeout=VERSION_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    return (result.stdout or "").strip() or None


def install_chrome(*, force=False, url=None):
    if not sys.platform.startswith("linux"):
        msg = f"L'installation automatique de Chrome n'est prise en charge que sous Linux (système : {sys.platform})."
        raise BrowserError(msg)

    if chrome_installed() and not force:
        version = chrome_version()

        info(f"Chrome déjà installé : {version or BROWSER_CHROME_PATH}.")

        return {"installed": True, "path": str(BROWSER_CHROME_PATH), "version": version, "skipped": True}

    source = url or BROWSER_CHROME_DEB_URL
    parsed = urlparse(source)

    if parsed.scheme != "https" or not parsed.netloc:
        msg = f"URL de téléchargement invalide (HTTPS requis) : {source}"
        raise BrowserError(msg)

    with tempfile.TemporaryDirectory(prefix="igscraper-chrome-") as directory:
        deb = Path(directory) / "google-chrome.deb"

        info(f"Téléchargement de Chrome depuis {source}…")
        _download(source, deb, _progress)
        info("Extraction de Chrome…")

        data = _extract_ar_member(deb, Path(directory))

        if data is None:
            msg = "Paquet .deb invalide : archive « data.tar » introuvable."
            raise BrowserError(msg)

        _install_tree(data)

    version = chrome_version()

    if version is None:
        msg = f"Chrome a été extrait mais ne démarre pas : {BROWSER_CHROME_PATH}"
        raise BrowserError(msg)

    info(f"Chrome installé : {version}.")

    return {"installed": True, "path": str(BROWSER_CHROME_PATH), "version": version, "skipped": False}


def clean_targets(profiles=(), *, keep_default_profile=False, keep_chrome=False):
    candidates = []

    if not keep_chrome:
        candidates.append(BROWSER_VENDOR_DIR)

    if not keep_default_profile:
        candidates.append(BROWSER_PROFILE_DIR)

    candidates.extend(Path(profile).expanduser() for profile in profiles)

    targets = []

    for candidate in candidates:
        resolved = candidate.resolve()

        _check_target(resolved)

        if resolved not in targets:
            targets.append(resolved)

    return targets


def clean_chrome(targets, *, dry_run=False):
    removed = []
    total = 0

    for target in targets:
        if not target.exists() and not target.is_symlink():
            debug(f"Élément absent : {target}.")

            continue

        size = tree_size(target)

        if dry_run:
            info(f"À supprimer : {target} ({format_size(size)}).")
        else:
            _remove(target)
            info(f"Supprimé : {target} ({format_size(size)}).")

        removed.append(str(target))
        total += size

    return {"removed": removed, "bytes": total, "dryRun": dry_run}


def tree_size(path):
    if path.is_symlink() or path.is_file():
        try:
            return path.lstat().st_size
        except OSError:
            return 0

    total = 0

    for root, _directories, files in os.walk(path):
        for name in files:
            try:
                total += (Path(root) / name).lstat().st_size
            except OSError:
                continue

    return total


def format_size(size):
    value = float(size)

    for unit in SIZE_UNITS:
        if value < SIZE_BASE or unit == SIZE_UNITS[-1]:
            return f"{value:.0f} {unit}" if unit == SIZE_UNITS[0] else f"{value:.1f} {unit}"

        value /= SIZE_BASE

    return f"{value:.1f} {SIZE_UNITS[-1]}"


def _progress(percent, done, total):
    info(f"Téléchargement de Chrome : {percent} % ({format_size(done)} / {format_size(total)}).")


def _download(url, destination, progress):
    request = Request(url, headers={"User-Agent": "igscraper"})  # noqa: S310

    try:
        with urlopen(request, timeout=DOWNLOAD_TIMEOUT) as response, destination.open("wb") as handle:  # noqa: S310
            total = int(response.headers.get("Content-Length") or 0)
            done = 0
            next_mark = PROGRESS_STEP

            while True:
                chunk = response.read(DOWNLOAD_BLOCK)

                if not chunk:
                    break

                handle.write(chunk)
                done += len(chunk)

                if total:
                    percent = done * 100 // total

                    if percent >= next_mark:
                        progress(percent, done, total)

                        next_mark = percent + PROGRESS_STEP
    except (OSError, URLError) as exc:
        msg = f"Téléchargement de Chrome impossible ({summarize(exc)})."
        raise BrowserError(msg) from exc

    if not destination.is_file() or destination.stat().st_size == 0:
        msg = f"Téléchargement de Chrome vide : {url}"
        raise BrowserError(msg)


def _extract_ar_member(deb, directory):
    with deb.open("rb") as archive:
        if archive.read(len(AR_MAGIC)) != AR_MAGIC:
            msg = "Paquet .deb invalide : signature « ar » absente."
            raise BrowserError(msg)

        while True:
            header = archive.read(AR_HEADER_SIZE)

            if not header:
                return None

            if len(header) < AR_HEADER_SIZE or header[AR_MAGIC_OFFSET : AR_MAGIC_OFFSET + 2] != b"`\n":
                msg = "Paquet .deb invalide : en-tête « ar » corrompu."
                raise BrowserError(msg)

            name = header[:AR_NAME_SIZE].decode("ascii", "replace").strip().rstrip("/")

            try:
                size = int(header[AR_SIZE_OFFSET : AR_SIZE_OFFSET + AR_SIZE_LENGTH].decode("ascii").strip())
            except ValueError as exc:
                msg = f"Paquet .deb invalide : taille illisible pour « {name} »."
                raise BrowserError(msg) from exc

            if not name.startswith(CHROME_DEB_MEMBER):
                archive.seek(size + size % 2, 1)

                continue

            target = directory / Path(name).name

            with target.open("wb") as handle:
                _copy_exact(archive, handle, size)

            if size % 2:
                archive.seek(1, 1)

            return target


def _copy_exact(source, destination, size):
    remaining = size

    while remaining:
        chunk = source.read(min(DOWNLOAD_BLOCK, remaining))

        if not chunk:
            msg = "Paquet .deb tronqué pendant l'extraction."
            raise BrowserError(msg)

        destination.write(chunk)
        remaining -= len(chunk)


def _install_tree(archive):
    staging = BROWSER_VENDOR_DIR / CHROME_STAGING

    if staging.exists():
        shutil.rmtree(staging)

    staging.mkdir(parents=True)

    try:
        _extract_chrome(archive, staging)

        tree = staging.joinpath(*CHROME_TREE)

        if not (tree / CHROME_BINARY).is_file():
            msg = f"Paquet .deb invalide : binaire « {CHROME_BINARY} » introuvable."
            raise BrowserError(msg)

        if BROWSER_CHROME_DIR.exists():
            shutil.rmtree(BROWSER_CHROME_DIR)

        tree.rename(BROWSER_CHROME_DIR)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def _extract_chrome(archive, staging):
    try:
        with tarfile.open(archive) as tar:
            for member in tar.getmembers():
                if not _is_chrome_member(member.name):
                    continue

                _extract_member(tar, member, staging)
    except (OSError, tarfile.TarError) as exc:
        msg = f"Extraction de Chrome impossible ({summarize(exc)})."
        raise BrowserError(msg) from exc


def _is_chrome_member(name):
    parts = _member_parts(name)

    return parts[: len(CHROME_TREE)] == CHROME_TREE


def _member_parts(name):
    path = PurePosixPath(name)
    parts = tuple(part for part in path.parts if part not in ("", "."))

    if path.is_absolute() or ".." in parts:
        msg = f"Archive Chrome invalide : chemin refusé « {name} »."
        raise BrowserError(msg)

    return parts


def _extract_member(tar, member, staging):
    parts = _member_parts(member.name)
    target = staging.joinpath(*parts)

    if member.isdir():
        target.mkdir(parents=True, exist_ok=True)

        return

    target.parent.mkdir(parents=True, exist_ok=True)

    if member.issym():
        link = PurePosixPath(member.linkname)

        if link.is_absolute() or ".." in link.parts:
            msg = f"Archive Chrome invalide : lien refusé « {member.linkname} »."
            raise BrowserError(msg)

        target.symlink_to(member.linkname)

        return

    if member.islnk():
        msg = f"Archive Chrome invalide : lien physique inattendu « {member.name} »."
        raise BrowserError(msg)

    source = tar.extractfile(member)

    if source is None:
        return

    with source, target.open("wb") as handle:
        shutil.copyfileobj(source, handle)

    target.chmod(member.mode & 0o777)


def _remove(target):
    try:
        if target.is_symlink() or target.is_file():
            target.unlink()
        else:
            shutil.rmtree(target)
    except OSError as exc:
        msg = f"Suppression impossible ({target}) : {summarize(exc)}"
        raise BrowserError(msg) from exc


def _check_target(path):
    root = PROJECT_ROOT.resolve()
    forbidden = {Path(path.anchor), Path.home().resolve(), root, *root.parents}

    if path in forbidden:
        msg = f"Répertoire refusé (trop large) : {path}"
        raise BrowserError(msg)


__all__ = [
    "chrome_installed",
    "chrome_version",
    "clean_chrome",
    "clean_targets",
    "format_size",
    "install_chrome",
    "tree_size",
]
