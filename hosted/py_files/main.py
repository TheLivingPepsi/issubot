from handlers.utilities_handler import *
from handlers import log_handler, version_handler, bot_handler

import os


def main():
    log_handler.create_logging()
    version_handler.check_version()

    token = os.environ["TOK_dcdbt"].replace('"', "")
    bot = bot_handler.create_bot(DIRS["json"] + "\\bot_settings.json")

    bot.run(token=token, log_handler=None)


if __name__ == "__main__":
    main()
