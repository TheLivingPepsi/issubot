### --- IMPORTS --- ###
import os
import time
import discord; from discord.ext import commands; from discord import interactions
import logging, logging.handlers
import requests, platform, json
import util
import random
import asyncio

### --- VARS / FUNCTIONS --- ###
base = os.environ["BASEPATH"].replace("\"", "")

DIRS = {
    "logging": base+"\\logging_files",
    "py": base+"\\py_files",
    "json": base+"\\json_files"
}

clear = lambda: (os.system('cls' if os.name == "nt" else 'clear'), print(COLORS.RESET))

sleep = lambda x: time.sleep(x)

class COLORS:
    DISCORD_GREEN = ""
    DISCORD_RED = ""
    DISCORD_YELLOW = ""
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    RESET = "\033[0m"

def create_bot(filepath: str = None):
    set_dict = {
        "activity": None,
        "allowed_mentions": discord.AllowedMentions.none(),
        "command_prefix": "!",
        "description": "A Discord bot.",
        "help_command": commands.DefaultHelpCommand(),
        "intents": discord.Intents.all()
    }

    if filepath != None:
        settings_file = json.load(open(filepath))
        prefix_mention, other_prefixes = False, False

        set_dict["activity"] = util.craft_activity(random.choice(settings_file["activities"]))
        set_dict["allowed_mentions"] = discord.AllowedMentions(
            everyone = settings_file["allowed_mentions"]["everyone"],
            users = settings_file["allowed_mentions"]["users"],
            roles = settings_file["allowed_mentions"]["roles"],
            replied_user = settings_file["allowed_mentions"]["replied_user"]            
        )

        for prefix in settings_file["command_prefix"]:
            if prefix == "@":
                prefix_mention = True
            elif other_prefixes:
                break
            else:
                other_prefixes = True

        if prefix_mention and other_prefixes:
            set_dict["command_prefix"] = commands.when_mentioned_or(*settings_file["command_prefix"][1:])
        elif prefix_mention:
            set_dict["command_prefix"] = commands.when_mentioned
        elif other_prefixes:
            set_dict["command_prefix"] = settings_file["command_prefix"]

        set_dict["description"] = settings_file["description"]

        '''
        TODO: make custom help command.
        https://discordpy.readthedocs.io/en/latest/ext/commands/api.html#ext-commands-help-command
        '''

        if not settings_file["help_command"]["default"]:
            set_dict["help_command"] = commands.HelpCommand(
                show_hidden = set_dict["help_command"]["command"]["show_hidden"],
                verify_checks = set_dict["help_command"]["command"]["verify_checks"]
            )

    return commands.Bot(
        activity = set_dict["activity"],
        allowed_mentions = set_dict["allowed_mentions"],
        command_prefix = set_dict["command_prefix"],
        description = set_dict["description"],
        help_command = set_dict["help_command"],
        intents = set_dict["intents"]
    )

### --- SETUP --- ###
## -- Logging -- ##
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
logging.getLogger('discord.http').setLevel(logging.INFO)

handler = logging.handlers.RotatingFileHandler(
    filename= DIRS["logging"]+"\\discord.log",
    encoding= 'utf-8',
    maxBytes= 32 * 1024 * 1024,  # 32 MiB
    backupCount=5,
)
dt_fmt = '%Y-%m-%d %H:%M:%S'
formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
handler.setFormatter(formatter)
logger.addHandler(handler)

## -- Bot Setup -- ##
### Bot Class

bot = create_bot(DIRS["json"]+"\\bot_settings.json")

### --- STARTUP --- ###
## -- Python Install -- ##
clear()

local_version = platform.python_version()

try:
    (r := requests.get('https://endoflife.date/api/python.json')).raise_for_status()
    latest_version = r.json()[0]["latest"]
except:
    latest_version = "UNKNOWN [unable to find latest Python version]"
print(COLORS.BOLD + "Local Python Installation: " + COLORS.YELLOW + COLORS.UNDERLINE + local_version + COLORS.RESET)
print(COLORS.BOLD + "Latest Python Version: " + COLORS.YELLOW + COLORS.UNDERLINE +  latest_version + COLORS.RESET)

if (latest_version != local_version and latest_version != "UNKNOWN [unable to find latest Python version]"):
    print(COLORS.RED + COLORS.BOLD + COLORS.UNDERLINE + "Your Python installation is out-of-date! You should probably update it.")
    sleep(2)
else:
    print(COLORS.GREEN + COLORS.BOLD + "Your Python installation is up-to-date!")
    sleep(0.2)

print(COLORS.RESET + "------------------")

## -- discord.py Install -- ##
local_version = discord.__version__
try:
    (r := requests.get('https://pypi.org/pypi/discord.py/json')).raise_for_status()
    latest_version = list(json.loads(r.text)["releases"].keys())[-1]
except:
    latest_version = "UNKNOWN [unable to find latest discord.py version]"
print(COLORS.BOLD + "Local discord.py Version: " + COLORS.YELLOW + COLORS.UNDERLINE + local_version + COLORS.RESET)
print(COLORS.BOLD + "Latest discord.py Version: " + COLORS.YELLOW + COLORS.UNDERLINE +  latest_version + COLORS.RESET)

if (latest_version != local_version and latest_version != "UNKNOWN [unable to find latest discord.py version]"):
    print(COLORS.RED + COLORS.BOLD + COLORS.UNDERLINE + "Your discord.py installation is out-of-date! You should probably update it.")
    sleep(2)
else:
    print(COLORS.GREEN + COLORS.BOLD + "Your discord.py installation is up-to-date!")
    sleep(0.2)

print(COLORS.RESET + "------------------")

## -- Start Bot -- ##
token = os.environ["TOK_dcdbt"].replace("\"", "")

bot.run(token=token, log_handler=None)
clear()
print("[issu]bot has shut down!\n")