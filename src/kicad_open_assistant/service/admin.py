"""Offline administrator CLI. Never prints provider keys or access tokens."""
import argparse
from decimal import Decimal
import os
from pathlib import Path
import re
from .ledger import Ledger


def money(value):
    amount = Decimal(value) * 1_000_000
    if not amount.is_finite() or amount < 0 or amount != int(amount):
        raise ValueError("Use nonnegative USD with at most six decimal places.")
    return int(amount)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=os.environ.get("KOA_LEDGER", "/data/ledger.sqlite3"))
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init")
    commands.add_parser("kill")
    enable = commands.add_parser("enable")
    enable.add_argument("--budget-usd", required=True)
    issue = commands.add_parser("issue")
    issue.add_argument("user")
    issue.add_argument("--allowance-usd", required=True)
    issue.add_argument("--token-file", type=Path, required=True)
    revoke = commands.add_parser("revoke")
    revoke.add_argument("user")
    inspect = commands.add_parser("status")
    inspect.add_argument("user")
    args = parser.parse_args()
    ledger = Ledger(args.db)
    if args.command == "init":
        ledger.initialize()
        print("Ledger initialized with sponsored access disabled and zero budget.")
    elif args.command == "kill":
        ledger.kill()
        print("Sponsored access disabled. Existing reservations remain charged.")
    elif args.command == "enable":
        from .app import Config
        config = Config(database=args.db, enabled=True, secret_file=os.environ.get("KOA_OPENAI_SECRET_FILE", ""), price_valid_until=os.environ.get("KOA_PRICE_VALID_UNTIL", "2000-01-01"))
        config.check()
        config.read_key()  # Check actual readability as the service UID, without printing it.
        ledger.configure(money(args.budget_usd), True)
        print("Ledger allowance set. Server must also have KOA_SPONSORED_ENABLED=true.")
    elif args.command == "issue":
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", args.user):
            parser.error("Use a short non-personal user identifier.")
        # Check destination before rotation so a typo cannot silently lose a token.
        descriptor = os.open(args.token_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(ledger.issue(args.user, money(args.allowance_usd)))
        print("Access token written to the specified private file. Deliver it using a secure channel; it is not an OpenAI key.")
    elif args.command == "revoke":
        ledger.revoke(args.user)
        print("Access revoked. No allowance was refunded.")
    elif args.command == "status":
        print(ledger.status(args.user))


if __name__ == "__main__":
    main()
