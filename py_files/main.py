from handlers import log_handler, version_handler, bot_handler
import os, sys


def main(args) -> None:
    log_handler.create_logging()
    version_handler.check_version()

    token = os.environ[args[1]].replace('"', "") if len(args) >= 2 else None
    bot = bot_handler().create_bot(version=args[2])

    bot.run(token=token)


if __name__ == "__main__":
    main(sys.argv)
