import discord, roblox
import json, random, requests, platform
import logging, logging.handlers as handlers
import os, os.path as path
import issutilities, issutilities.craft as craft, issutilities.directories as directories, issutilities.colors as COLORS
import objects
from discord.ext import commands
from typing import Any, cast

class startup_handler:
    @staticmethod
    def __get_bot_settings(given_path: str = __file__, settings_iter: int | None = None) -> str:
        a = path.dirname(given_path)
        json_file = path.join(a, "..", "json_files", f"bot_settings{f"_{settings_iter}" if settings_iter else ""}.json")
        if not os.path.exists(json_file):
            raise FileNotFoundError("Missing bot_settings.json file!")
        
        return json_file
    
    @classmethod
    def get_startup_payload(cls, given_path: str = __file__, args: list[str] | None = []) -> tuple:
        args = cast(list[str], args)

        try:
            settings_iter = int(args[1])
        except (ValueError, IndexError):
            settings_iter = None

        with open(cls.__get_bot_settings(given_path, settings_iter)) as f:
            bot_settings = json.load(f)

        botname = bot_settings.pop("botname", "Error")
        is_test = bot_settings.pop("is_test", False)

        token = (
            os.getenv("TESSUBOT_TOKEN" if is_test else "ISSUBOT_TOKEN") 
            if botname == "issubot" 
            else os.getenv("DJTESSU_TOKEN" if is_test else "DJISSU_TOKEN") 
            if botname == "djissu" 
            else None
        )

        if not token:
            raise KeyError(f"Missing token! The botname is incorrect or the token is not available. Given botname: {botname}")

        return bot_settings, token, botname

class bot_handler:
    @staticmethod
    def __get_owner_id() -> int | None:
        return int(os.getenv("OWNER_ID", "0").replace('"', ""))

    @staticmethod
    def __setup_core(bot: objects.Bot) -> None:
        @bot.command(aliases=["reload", "reload_cogs", "reload_extensions", "load", "load_cogs", "load_extensions", "unload", "unload_cogs", "unload_extensions"])
        @commands.is_owner()
        async def extension(ctx: commands.Context, raw_action: str | None, *args):
            extracted_action = None if not ctx.invoked_with else (ctx.invoked_with).split(sep="_")[0]
            action = raw_action or extracted_action or "None"

            extensions = list(args) if len(args) > 0 else None

            try:
                match action := action.lower():
                    case "reload":
                        await bot.reload_extensions(extensions)
                    case "load":
                        await bot.load_extensions(extensions)
                    case "unload":
                        await bot.unload_extensions(extensions)
                    case _:
                        await ctx.reply(f"Invalid action! Provided action: {action}")
            except Exception as e:
                await ctx.reply(f"Extension action {action} failed: {e}")
                raise e
            else:
                await ctx.reply("Done!")

        @bot.command(aliases=["shutdown", "close"])
        @commands.is_owner()
        async def restart(ctx):
            """Stops the bot. In a production environment, it should automatically reboot and come back online."""
            
            bot.__print_with_divider()
            print(f"{COLORS.BOLD}Shutting down {bot.user.name}...{COLORS.RESET}")
            await ctx.reply("Bot is shutting down...")
            await bot.change_presence(status=discord.Status.idle)
            await bot.close()

        @bot.command(aliases=["latency", "test"])
        async def ping(ctx):
            """Displays the bot's latency/ping."""
            bot_latency = round(bot.latency * 1000, 2)

            await ctx.reply(f"🏓 Pong!\n- Bot latency: {bot_latency}ms")

    @classmethod
    def create_bot(cls, startup_payload: tuple[dict, str, str], startup_notifs: dict[str, str]) -> tuple[objects.Bot, str]:
        (bot_settings, token, botname) = startup_payload

        help_command = objects.HelpCommand()
        activities = [craft.an.activity(activity_payload) for activity_payload in bot_settings.get("activities", [])]

        bot = objects.Bot(
            activity=random.choice(activities) if len(activities) > 0 else None,
            all_activities=activities,
            allowed_mentions=craft.an.allowed_mentions(bot_settings.get("allowed_mentions")),
            command_prefix=craft.a.prefix(bot_settings.get("command_prefix")),
            description=bot_settings.get("description"),
            help_command=help_command,
            intents=craft.an.intents(bot_settings.get("intents")),
            case_insensitive=bot_settings.get("case_insensitive"),
            owner_id = cls.__get_owner_id(),
            botname=botname,
            startup_notifs=startup_notifs
        )

        cls.__setup_core(bot)

        return bot, token

    @staticmethod
    def run(bot: objects.Bot | commands.Bot, token: str) -> None:
        bot.run(token, log_handler=None)

class logging_handler:
    @staticmethod
    def create_logger(botname: str | None = "issubot") -> None:
        DIRS = botname == "issubot" and directories.ISSUBOT or directories.DJISSU
      
        logging_file_name = f"{DIRS.LOGGING}/discord.log"

        open(logging_file_name, mode="a").close()

        logger = logging.getLogger('discord')
        logger.setLevel(logging.DEBUG)
        logging.getLogger('discord.http').setLevel(logging.INFO)

        handler = handlers.RotatingFileHandler(
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
    COMPARISONS = {
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

    @staticmethod
    def __compare_versions(
        current_version: str | None = "Unknown",
        latest_version: str | Any = "Unknown",
    ) -> str:
        desc_string = None

        if latest_version == "Unknown":
            desc_string = "is potentially outdated, but the latest version could not be checked."
        elif latest_version == current_version:
            desc_string = "is up-to-date!" 
        else:
            desc_string = "is outdated or was removed. Consider updating!"

        return f"{desc_string}\n - **Current**: {current_version}\n - **Latest**: {latest_version}"

    @staticmethod
    def __get_latest_version(url: str | None = "", source: str | None = None) -> str | Exception | None:
        try: 
            (request := requests.get(str(url))).raise_for_status()

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
    def get_version_payload(cls) -> dict[str, str]:
        version_payload = {
            name: cls.__compare_versions(
                payload["Current"], 
                cls.__get_latest_version(**(payload["Latest"]))
            ) 
            for name, payload in cls.COMPARISONS.items()
        }

        return version_payload
