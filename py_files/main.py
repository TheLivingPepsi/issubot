import sys
import issutilities.colors as COLORS
from handlers import *


def main(args: list | None = None) -> None:
    logging_handler.create_logger()

    startup_payload = startup_handler.get_startup_payload(args)
    version_payload = version_handler.get_version_payload()

    bot, token = bot_handler.create_bot(startup_payload, version_payload)

    bot_handler.run(bot, token)


if __name__ == "__main__":
    print(f"{COLORS.BOLD}Initializing...{COLORS.RESET}")
    main(sys.argv)
