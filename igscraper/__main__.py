import argparse
import asyncio
import json
import sys

from igscraper import BrowserOptions, Instagram, __version__, configure_logging
from igscraper.constants import error
from igscraper.errors import IGScraperError, LoginError
from igscraper.render import render
from igscraper.session import SessionOptions, establish_session_result


def _common_options(*, suppress=False):
    default = argparse.SUPPRESS if suppress else False

    parser = argparse.ArgumentParser(add_help=False)

    parser.add_argument(
        "--json",
        action="store_true",
        default=default,
        help="écrire uniquement le JSON final sur stdout, sans journal",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        default=default,
        help="afficher la fenêtre du navigateur (nécessaire pour un challenge)",
    )
    parser.add_argument(
        "--load-media",
        action="store_true",
        default=default,
        help="télécharger les images et vidéos (bloquées par défaut)",
    )
    parser.add_argument(
        "--sessionid",
        default=argparse.SUPPRESS if suppress else None,
        metavar="COOKIE",
        help="cookie sessionid à réutiliser",
    )
    parser.add_argument(
        "--username",
        default=argparse.SUPPRESS if suppress else None,
        metavar="USER",
        help="compte Instagram",
    )
    parser.add_argument(
        "--password",
        default=argparse.SUPPRESS if suppress else None,
        metavar="PASS",
        help="mot de passe",
    )
    parser.add_argument(
        "--log-level",
        default=argparse.SUPPRESS if suppress else None,
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="verbosité des journaux (défaut : INFO)",
    )

    return parser


def _command(subparsers, name, summary, common):
    return subparsers.add_parser(name, help=summary, parents=[common])


def _build_parser():
    common = _common_options()
    command_common = _common_options(suppress=True)

    parser = argparse.ArgumentParser(
        prog="igscraper",
        description="Client Instagram : connexion, recherche, profils, messages.",
        parents=[common],
    )
    parser.add_argument("--version", action="version", version=f"igscraper {__version__}")

    commands = parser.add_subparsers(dest="command", required=True, metavar="COMMANDE")

    _command(commands, "login", "se connecter et afficher le sessionid", command_common)
    _command(commands, "logout", "se déconnecter (effacer la session)", command_common)
    _command(commands, "disconnect", "se déconnecter (effacer la session)", command_common)

    search = _command(commands, "search", "rechercher des comptes", command_common)
    search.add_argument("query", help="texte recherché")

    account = _command(commands, "account", "afficher un profil", command_common)
    account.add_argument("username_arg", metavar="USER", help="compte à consulter")

    follow = _command(commands, "follow", "s'abonner à un compte", command_common)
    follow.add_argument("username_arg", metavar="USER", help="compte à suivre")

    messages = _command(commands, "messages", "lire une conversation", command_common)
    messages.add_argument("username_arg", metavar="USER", help="destinataire de la conversation")
    messages.add_argument("--last", type=int, metavar="N", help="n'afficher que les N derniers messages (0 = tous)")

    send = _command(commands, "send", "envoyer un message privé", command_common)
    send.add_argument("username_arg", metavar="USER", help="destinataire")
    send.add_argument("message", help="texte à envoyer")
    send.add_argument("--history", action="store_true", help="renvoyer l'historique après envoi")
    send.add_argument(
        "--last",
        type=int,
        metavar="N",
        help="avec --history : afficher les N derniers messages (défaut 10, 0 = tous)",
    )

    return parser


def _client(args):
    return Instagram(
        BrowserOptions(
            headless=not args.headed,
            block_media=not args.load_media,
        ),
    )


async def _authenticate(client, args):
    if args.sessionid:
        result = await client.login(sessionid=args.sessionid)
    else:
        result = await client.login(username=args.username, password=args.password)

    if not result:
        raise LoginError(result.reason or "connexion impossible")


async def _execute(args):
    if args.command == "login":
        return await _login_command(args)

    if args.command in ("logout", "disconnect"):
        async with _client(args) as client:
            await client.logout()
            return {"success": True}

    async with _client(args) as client:
        await _authenticate(client, args)

        return await _run_command(client, args)


async def _login_command(args):
    if args.sessionid:
        async with _client(args) as client:
            result = await client.login(sessionid=args.sessionid)

            if not result:
                raise LoginError(result.reason or "sessionid refusé")

            return {"sessionId": result.sessionid, "method": result.method}

    result = await establish_session_result(
        args.username,
        args.password,
        SessionOptions(headless=not args.headed),
    )

    if not result or not result.sessionid:
        raise LoginError(result.reason if result else "impossible d'obtenir un sessionid")

    return {"sessionId": result.sessionid, "method": result.method or "auto"}


async def _run_command(client, args):
    if args.command == "search":
        return await client.search(args.query)

    if args.command == "account":
        return await client.account(args.username_arg)

    if args.command == "follow":
        await client.follow(args.username_arg)

        return {"username": args.username_arg, "followed": True}

    if args.command == "messages":
        return await client.messages(args.username_arg)

    if args.command == "send":
        return await client.send_message(
            args.username_arg,
            args.message,
            history=args.history,
        )

    msg = f"commande inconnue : {args.command}"
    raise LoginError(msg)


def _emit(data, args):
    if args.json:
        sys.stdout.write(json.dumps(data, ensure_ascii=False, indent=2, default=str) + "\n")
    else:
        sys.stdout.write(render(args.command, data, getattr(args, "last", None)) + "\n")


def _fail(message, args):
    if args.json:
        sys.stdout.write(json.dumps({"error": message}, ensure_ascii=False, indent=2) + "\n")
    else:
        error(message)

    return 1


async def _run(args):
    try:
        data = await _execute(args)
    except IGScraperError as exc:
        return _fail(str(exc), args)

    if data is not None:
        _emit(data, args)

    return 0


def main(argv=None):
    args = _build_parser().parse_args(argv)

    configure_logging(args.log_level, quiet=args.json)

    try:
        return asyncio.run(_run(args))
    except KeyboardInterrupt:
        return _fail("Interrompu.", args)


if __name__ == "__main__":
    raise SystemExit(main())
