from handlers import log_handler, version_handler, lavalink_handler, bot_handler
import os


def main() -> None:
    log_handler.create_logging()
    version_handler.check_version()
    lavalink_handler.start()

    token = os.environ["TOK_dcdbt"].replace('"', "")
    bot = bot_handler().create_bot()

    bot.run(token=token)


if __name__ == "__main__":
    main()
