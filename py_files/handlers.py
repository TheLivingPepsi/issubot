import discord, json, random, requests, platform, roblox
import os, os.path as path
import logging, logging.handlers
import issutilities, issutilities.craft as craft, issutilities.directories as directories, issutilities.colors as COLORS
import objects
from discord.ext import commands

class startup_handler:
    @classmethod
    def __redirect_to_repo(self, given_path, settings_iter) -> str:
        mainpypath = path.realpath(given_path)
        pyfilesdir = path.dirname(mainpypath)
        repodir = path.dirname(pyfilesdir)
        json_file = path.join(repodir, f"json_files/bot_settings{settings_iter and f"_{settings_iter}" or ""}.json")
        if not os.path.exists(json_file):
            raise FileNotFoundError("Missing bot_settings.json file!")
        
        return json_file
    
    @classmethod
    def get_startup_payload(self, args: list | None = None, given_path: str | None = __file__) -> tuple:
        settings_iter = None
        try:
            settings_iter = int(args[1])
        except (ValueError, IndexError):
            pass

        bot_settings: dict = json.load(open(self.__redirect_to_repo(given_path, settings_iter)))
        botname = bot_settings.pop("botname", "Error")
        is_test = bot_settings.pop("is_test", False)

        token = botname == "issubot" and (
            (is_test and os.getenv("TESSUBOT_TOKEN")) or os.getenv("ISSUBOT_TOKEN")
            ) or botname == "djissu" and (
            (is_test and os.getenv("DJTESSU_TOKEN")) or os.getenv("DJISSU_TOKEN")
            ) or None
        
        if not token:
            raise KeyError(f"Missing botname key in bot settings! Given name: {botname}")

        return bot_settings, token, botname

class bot_handler:
    @classmethod
    def __get_owner_id(self) -> int:
        if "OWNER_ID" in os.environ:
            return int(os.environ["OWNER_ID"].replace('"', ""))

    @classmethod
    def __do_additional_setup(self, bot: objects.Bot | commands.Bot) -> None:
        bot._BotBase__cogs = commands.core._CaseInsensitiveDict() # makes cog arguments case-insensitive

        @bot.command(aliases=["reload", "reload_extensions"])
        @commands.is_owner()
        async def reload_cogs(ctx):
            """Reloads all extensions."""
            await ctx.reply("Reloading extensions!")
            await bot.reload_cogs()

        @bot.command(aliases=["shutdown", "close"])
        @commands.is_owner()
        async def restart(ctx: commands.Context):
            """Stops the bot. In a production environment, it should automatically reboot and come back online."""
            
            bot.print_divider()
            print(f"{COLORS.BOLD}Shutting down {bot.user.name}...{COLORS.RESET}")
            await ctx.reply("Bot is shutting down...")
            await bot.change_presence(status=discord.Status.idle)
            await bot.close()

        @bot.command(aliases=["latency", "test"])
        async def ping(ctx: commands.Context):
            """Displays the bot's latency/ping."""
            bot_latency = round(bot.latency * 1000, 2)

            await ctx.reply(f"🏓 Pong!\n- Bot latency: {bot_latency}ms")

    @classmethod
    def create_bot(self, startup_payload: tuple, startup_notifs: list) -> objects.Bot | str:
        (bot_settings, token, botname) = startup_payload

        help_command = commands.DefaultHelpCommand() # classes.HelpCommand()
        activities = None

        for payload in bot_settings["activities"]:
            if activities is None:
                activities = []
            activities.append(craft.an.activity(payload))

        bot = objects.Bot(
            activity=activities and random.choice(activities) or None,
            all_activities=activities,
            allowed_mentions=craft.an.allowed_mentions(bot_settings["allowed_mentions"]),
            command_prefix=craft.a.prefix(bot_settings["command_prefix"]),
            description=bot_settings["description"],
            help_command=help_command,
            intents=craft.an.intents(bot_settings["intents"]),
            case_insensitive=bot_settings["case_insensitive"],
            owner_id = self.__get_owner_id(),
            botname=botname,
            startup_notifs=startup_notifs
        )

        self.__do_additional_setup(bot)

        return bot, token

    @classmethod
    def run(self, bot: objects.Bot | commands.Bot, token: str) -> None:
        bot.run(token, log_handler=None)
class logging_handler:
    @classmethod
    def create_logger(self, botname: str | None = "issubot") -> None:
        DIRS = botname == "issubot" and directories.ISSUBOT or directories.DJISSU
      
        logging_file_name = f"{DIRS.LOGGING}/discord.log"

        if not path.exists(DIRS.LOGGING):
            os.makedirs(DIRS.LOGGING, exist_ok=True)

        if not path.exists(logging_file_name):
            open(logging_file_name, mode="x").close()


        logger = logging.getLogger('discord')
        logger.setLevel(logging.DEBUG)
        logging.getLogger('discord.http').setLevel(logging.INFO)

        handler = logging.handlers.RotatingFileHandler(
            filename=logging_file_name,
            encoding='utf-8',
            maxBytes=32 * 1024 * 1024,  # 32 MiB
            backupCount=5,  # Rotate through 5 files
        )
        dt_fmt = '%Y-%m-%d %H:%M:%S'
        formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

class version_handler:
    comparisons = {
        "Python": {
            "Current": platform.python_version(),
            "Latest": {
                "url": "https://endoflife.date/api/python.json",
                "source": "EOL",
            }
        },
        "discord.py": {
            "Current": discord.__version__,
            "Latest": {
                "url": "https://pypi.org/pypi/discord.py/json",
                "source": "PyPi",
            }
        },
        "ro.py": {
            "Current": roblox.__version__,
            "Latest": {
                "url": "https://pypi.org/pypi/roblox/json",
                "source": "PyPi",
            }
        },
        "issutilities": {
            "Current": issutilities.__version__,
            "Latest": {
                "url": "https://pypi.org/pypi/issutilities/json",
                "source": "PyPi",
            }
        }
    }

    @classmethod
    def __compare_versions(
        self,
        current_version: str | None = "Unknown",
        latest_version: str | None = "Unknown",
    ) -> str:
        desc_string = None

        if latest_version == "Unknown":
            desc_string = "is potentially outdated, but the latest version could not be checked."
        elif latest_version != current_version:
            desc_string = "is outdated or was removed. Consider updating!"
        else:
            desc_string = "is up-to-date!" 
    
        return f"{desc_string}\n - **Current**: {current_version}\n - **Latest**: {latest_version}"

    @classmethod
    def __get_latest_version(self, url: str | None = None, source: str | None = None) -> str | None:
        try: 
            (request := requests.get(url)).raise_for_status()

            json_data = request.json()

            match source:
                case "EOL":
                    return json_data[0]["latest"]
                case "PyPi":
                    return json_data["info"]["version"]
                case _:
                    return "Invalid source"
        except Exception as e:
            return e

    @classmethod
    def get_version_payload(self) -> dict:
        version_payload = {}

        for name, payload in self.comparisons.items():
            latest_version = self.__get_latest_version(**(payload["Latest"]))
            version_payload[name] = self.__compare_versions(payload["Current"], latest_version)

        return version_payload
