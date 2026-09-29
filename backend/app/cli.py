"""Account management: ``python -m app.cli <command>`` (run from backend/).

    create-user NAME     create an account (asks for the password)
    set-password NAME    change a password and log the user out everywhere
    rename-user OLD NEW  change a username
    list-users           show all accounts
    check                warn about a missing account or password (used by start.ps1)

``--password-stdin`` reads the password from standard input instead (for scripts).
"""

import argparse
import getpass
import sys
from datetime import timedelta

from app.core.exceptions import AppError
from app.db.session import SessionLocal
from app.services.auth import AuthService, LoginThrottle


def _read_password(from_stdin: bool) -> str:
    if from_stdin:
        return sys.stdin.readline().rstrip("\r\n")
    password = getpass.getpass("Şifre: ")
    if getpass.getpass("Şifre (tekrar): ") != password:
        raise SystemExit("Şifreler aynı değil.")
    return password


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="Manage accounts.")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("create-user", "set-password"):
        command = commands.add_parser(name)
        command.add_argument("username")
        command.add_argument("--password-stdin", action="store_true")
    rename = commands.add_parser("rename-user")
    rename.add_argument("username")
    rename.add_argument("new_username")
    commands.add_parser("list-users")
    commands.add_parser("check")
    args = parser.parse_args(argv)

    with SessionLocal() as session:
        # Session lifetime and throttle are irrelevant for account management.
        service = AuthService(session, session_lifetime=timedelta(days=1), throttle=LoginThrottle())
        try:
            if args.command == "create-user":
                user = service.create_user(
                    username=args.username, password=_read_password(args.password_stdin)
                )
                print(f"Kullanıcı oluşturuldu: {user.username} (id {user.id})")
            elif args.command == "set-password":
                user = service.set_password(
                    username=args.username, password=_read_password(args.password_stdin)
                )
                print(f"Şifre değişti: {user.username}. Bütün oturumları kapatıldı.")
            elif args.command == "rename-user":
                user = service.rename_user(username=args.username, new_username=args.new_username)
                print(f"Kullanıcı adı değişti: {user.username}")
            elif args.command == "check":
                users = service.list_users()
                if not users:
                    print("UYARI: Hiç kullanıcı yok. Oluştur: python -m app.cli create-user <ad>")
                for user in users:
                    if not user.password_hash:
                        print(
                            f"UYARI: '{user.username}' kullanıcısının şifresi yok. "
                            f"Belirle: python -m app.cli set-password {user.username}"
                        )
            else:
                for user in service.list_users():
                    state = "" if user.password_hash else "  (şifre yok, giriş kapalı)"
                    print(f"{user.id}\t{user.username}{state}")
        except AppError as exc:
            print(f"Hata: {exc.message}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
