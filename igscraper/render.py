import json
import os
import shutil
import sys
import textwrap
import unicodedata
from datetime import datetime

from igscraper.constants import (
    RENDER_ACCOUNT_WIDTH,
    RENDER_ANSI,
    RENDER_BUBBLE_INDENT,
    RENDER_BUBBLE_MARGIN,
    RENDER_BUBBLE_MAX_TEXT,
    RENDER_BUBBLE_MIN_TEXT,
    RENDER_BUBBLE_RATIO,
    RENDER_DAYS,
    RENDER_EMOJI_START,
    RENDER_EMPTY,
    RENDER_MONTHS,
    RENDER_PAGED_COMMANDS,
    RENDER_PLURAL_MIN,
    RENDER_POST_DESCRIPTION_LINES,
    RENDER_RULE_MAX,
    RENDER_SEND_DEFAULT_LAST,
    RENDER_STYLES,
    RENDER_TERM_DEFAULT,
    RENDER_TERM_HEIGHT,
    RENDER_TERM_MAX,
    RENDER_TERM_MIN,
    RENDER_TODAY,
    RENDER_YESTERDAY,
    RENDER_ZERO_WIDTH,
    RENDERER_NAMES,
)


def _color_enabled():
    if os.environ.get("NO_COLOR"):
        return False

    if os.environ.get("FORCE_COLOR"):
        return True

    return sys.stdout.isatty()


def _paint(text, *styles):
    if not styles or not _color_enabled():
        return text

    codes = ";".join(RENDER_STYLES[style] for style in styles)

    return f"\033[{codes}m{text}\033[0m"


def _width(text):
    total = 0

    for char in RENDER_ANSI.sub("", text):
        if char in RENDER_ZERO_WIDTH or unicodedata.combining(char):
            continue

        wide = unicodedata.east_asian_width(char) in {"W", "F"} or ord(char) >= RENDER_EMOJI_START
        total += 2 if wide else 1

    return total


def _pad(text, width):
    return text + " " * max(width - _width(text), 0)


def _term():
    columns = shutil.get_terminal_size((RENDER_TERM_DEFAULT, RENDER_TERM_HEIGHT)).columns

    return max(RENDER_TERM_MIN, min(columns, RENDER_TERM_MAX))


def _center(text, width):
    return " " * max((width - _width(text)) // 2, 0) + text


def _rule(width=None):
    return _paint("─" * (width or min(_term(), RENDER_RULE_MAX)), "gray")


def _title(icon, text, subtitle=None):
    head = f"{icon}  {_paint(text, 'bold')}"

    if subtitle:
        head += "  " + _paint(subtitle, "gray")

    return [head, _rule()]


def _value(value):
    if value is None or value == "":
        return _paint(RENDER_EMPTY, "gray")

    return str(value)


def _number(value):
    if value is None:
        return RENDER_EMPTY

    try:
        return f"{int(value):,}".replace(",", "\u202f")
    except (TypeError, ValueError):
        return str(value)


def _plural(count, singular, plural=None):
    label = singular if count < RENDER_PLURAL_MIN else (plural or singular + "s")

    return f"{_number(count)} {label}"


def _to_datetime(value):
    try:
        return datetime.fromtimestamp(int(value))
    except (TypeError, ValueError, OSError, OverflowError):
        return None


def _day_label(day, today):
    delta = (today - day).days

    if delta == 0:
        return RENDER_TODAY

    if delta == 1:
        return RENDER_YESTERDAY

    return f"{RENDER_DAYS[day.weekday()]} {day.day} {RENDER_MONTHS[day.month - 1]} {day.year}".capitalize()


def _wrap(text, width):
    lines = []

    for raw in str(text).splitlines() or [""]:
        lines.extend(textwrap.wrap(raw, width, replace_whitespace=False) or [""])

    return lines


def _render_login(data):
    sessionid = data.get("sessionId") or ""

    lines = _title("🔑", "Connexion Instagram réussie")
    lines.append(f"  {_paint('Méthode', 'gray'):<12}  {_value(data.get('method'))}")
    lines.append(f"  {_paint('Session ID', 'gray'):<12}  {_paint(_value(sessionid), 'green')}")

    if sessionid:
        lines.append(f"  {_paint('Longueur', 'gray'):<12}  {len(sessionid)} caractères")

    return "\n".join(lines)


def _render_logout(_data):
    return f"🚪 {_paint('Déconnexion réussie', 'green')} (session effacée)."


def _render_follow(data):
    username = _paint(f"@{_value(data.get('username'))}", "bold")

    if data.get("followed"):
        return f"✨ {username} : {_paint('abonnement confirmé', 'green')}."

    return f"⚠️  {username} : {_paint('abonnement non confirmé', 'yellow')}."


def _render_search(accounts):
    if not accounts:
        return "🔍 Aucun compte trouvé."

    lines = _title("🔍", "Recherche Instagram", _plural(len(accounts), "compte trouvé", "comptes trouvés"))
    lines.append("")

    handles = [f"@{_value(account.get('username'))}" for account in accounts]
    column = max(_width(handle) for handle in handles)
    index_width = len(str(len(accounts)))

    for index, (account, handle) in enumerate(zip(accounts, handles, strict=True), 1):
        name = account.get("name")
        name = name if name and name != account.get("username") else ""
        followers = account.get("followersCount")

        if followers is not None:
            name = f"{name}  {_paint(_plural(followers, 'abonné'), 'gray')}".strip()

        lines.append(
            f"  {_paint(str(index).rjust(index_width), 'gray')}  "
            f"{_paint(_pad(handle, column), 'bold', 'cyan')}  {name}".rstrip(),
        )
        lines.append(f"  {' ' * index_width}  {_paint(_value(account.get('url')), 'gray')}")
        lines.append("")

    return "\n".join(lines).rstrip()


def _stat(count, label):
    return f"{_paint(_number(count), 'bold')} {label}"


def _render_posts(posts, width):
    lines = ["", *_title("📸", "Dernières publications", f"({len(posts)})")]

    if not posts:
        lines.append(_paint("  Aucune publication visible.", "gray"))

        return lines

    lines.append("")
    index_width = len(str(len(posts)))
    text_width = width - index_width - 4

    for index, post in enumerate(posts, 1):
        description = " ".join((post.get("description") or "").split()) or "(sans description)"
        shortened = textwrap.shorten(description, text_width * RENDER_POST_DESCRIPTION_LINES, placeholder="…")
        wrapped = textwrap.wrap(shortened, text_width) or [shortened]

        lines.append(f"  {_paint(str(index).rjust(index_width), 'gray')}  {wrapped[0]}")
        lines.extend(f"  {' ' * index_width}  {line}" for line in wrapped[1:])

    return lines


def _render_account(data):
    width = min(_term(), RENDER_ACCOUNT_WIDTH)

    badges = []

    if data.get("appearsPrivate"):
        badges.append(_paint("🔒 privé", "yellow"))

    if data.get("isFollowed"):
        badges.append(_paint("✔ suivi(e)", "green"))

    head = _paint(f"@{_value(data.get('username'))}", "bold", "cyan")

    if data.get("name"):
        head += f"  {data['name']}"

    lines = [f"👤 {head}"]

    if badges:
        lines.append("   " + "  ".join(badges))

    lines.extend(
        [
            _rule(width),
            "  "
            + _paint("  ·  ", "gray").join(
                [
                    _stat(data.get("postsCount"), "publications"),
                    _stat(data.get("followersCount"), "abonnés"),
                    _stat(data.get("followingCount"), "abonnements"),
                ],
            ),
        ],
    )

    bio = data.get("bio")

    if bio:
        lines.append("")
        lines.extend(f"  {line}" for line in _wrap(bio, width - 4))

    extras = [("📍", data.get("address")), ("🔗", data.get("url"))]
    extras = [(icon, value) for icon, value in extras if value]

    if extras:
        lines.append("")
        lines.extend(f"  {icon} {value}" for icon, value in extras)

    lines.extend(_render_posts(data.get("latestPosts") or [], width))

    return "\n".join(lines)


def _bubble(content, stamp, *, mine, term):
    max_text = max(RENDER_BUBBLE_MIN_TEXT, min(int(term * RENDER_BUBBLE_RATIO), RENDER_BUBBLE_MAX_TEXT))
    body = _wrap(content.strip() or "(message vide)", max_text)

    inner = max(_width(stamp) + 2, *(_width(line) for line in body))
    color = "green" if mine else "cyan"
    indent = " " * (term - inner - RENDER_BUBBLE_INDENT if mine else RENDER_BUBBLE_MARGIN)

    top = _paint(f"╭{'─' * (inner + 2)}╮", color)
    bottom = _paint(f"╰{'─' * (inner - _width(stamp))} ", color) + _paint(stamp, "gray") + _paint(" ╯", color)
    edge = _paint("│", color)

    rows = [top, *(f"{edge} {_pad(line, inner)} {edge}" for line in body), bottom]

    return [indent + row for row in rows]


def _render_message_list(messages, last, term):
    hidden = 0

    if last and 0 < last < len(messages):
        hidden = len(messages) - last
        messages = messages[-last:]

    lines = []

    if hidden:
        lines.append(
            _paint(
                f"  … {_plural(hidden, 'message plus ancien masqué', 'messages plus anciens masqués')}"
                " (--last 0 pour tout afficher)",
                "gray",
            ),
        )

    today = datetime.now().date()
    current_day = None
    previous = None

    for message in messages:
        when = _to_datetime(message.get("timestamp"))
        mine = bool(message.get("isSelf"))
        sender = None if mine else (message.get("sender") or "inconnu")

        if when is not None and when.date() != current_day:
            current_day = when.date()
            previous = None
            label = f"── {_day_label(current_day, today)} ──"
            lines.extend(["", _paint(_center(label, term), "gray"), ""])

        key = (mine, sender)

        if key != previous:
            if previous is not None:
                lines.append("")

            if not mine:
                lines.append("  " + _paint(f"@{sender}", "bold", "cyan"))

        stamp = when.strftime("%H:%M") if when else "--:--"
        lines.extend(_bubble(str(message.get("content") or ""), stamp, mine=mine, term=term))
        previous = key

    return lines


def _conversation(username, messages, last):
    mine = sum(1 for message in messages if message.get("isSelf"))
    summary = f"{_plural(len(messages), 'message')} · {mine} envoyé(s) · {len(messages) - mine} reçu(s)"

    lines = _title("💬", f"Conversation avec @{username}", summary)

    if not messages:
        lines.append(_paint("  Aucun message.", "gray"))

        return lines

    lines.extend(_render_message_list(messages, last, _term()))

    return lines


def _render_messages(data, last=None):
    return "\n".join(_conversation(_value(data.get("username")), data.get("messages") or [], last))


def _render_send(data, last=None):
    username = _value(data.get("username"))
    messages = data.get("messages") or []

    lines = [f"🚀 {_paint('Message envoyé', 'green')} à {_paint(f'@{username}', 'bold')}."]

    if messages:
        lines.extend(["", *_conversation(username, messages, RENDER_SEND_DEFAULT_LAST if last is None else last)])

    return "\n".join(lines)


def render(command, data, last=None):
    renderer_name = RENDERER_NAMES.get(command)
    renderer = globals().get(renderer_name) if renderer_name else None

    if renderer is None:
        return json.dumps(data, ensure_ascii=False, indent=2, default=str)

    if command in RENDER_PAGED_COMMANDS:
        return renderer(data, last)

    return renderer(data)


paint = _paint


__all__ = ["paint", "render"]
