from handlers.log_handler import create_logging
from handlers.version_handler import check_version
import os
from util import *
from handlers.bot_handler import create_bot

def main():
    create_logging()
    check_version()

    token = os.environ["TOK_dcdbt"].replace("\"", "")
    bot = create_bot(DIRS["json"]+"\\bot_settings.json")

    bot.run(token=token, log_handler=None)

if __name__ == "__main__":
    main()