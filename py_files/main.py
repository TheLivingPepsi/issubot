import sys
from handlers import startup_handler, bot_handler, log_handler, version_handler


def main(args: list | None = None) -> None:
    log_handler.create_logger()

    startup_payload = startup_handler.get_startup_payload(args)
    version_payload = version_handler.get_version_payload()

    bot, token = bot_handler.create_bot(startup_payload, version_payload)

    bot.run(token=token)


if __name__ == "__main__":
    main(sys.argv)
