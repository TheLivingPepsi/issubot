import discord
from discord.ext import commands
import os
import roblox
import asyncio
import json
from issutilities import DIRS, craft, COLORS, actions
import random
import traceback
import platform

class bot_handler:
    class Bot(commands.Bot):
        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)
            rbxtoken = os.environ["TOK_rbxacc_hz"].replace('"', "")
            self.ro_client = roblox.Client(rbxtoken)
            self.logger = logging.getLogger("discord")

        def error_handler(self, task: asyncio.Task) -> None:
            exc = task.exception()
            if exc:
                print("----------")
                traceback.print_exception(exc)
                self.logger.error("An error occurred", exc_info=exc)

        async def run_once_when_ready(self) -> None:
            await self.wait_until_ready()
            print("----------\nLoading cogs...")
            await self.load_cogs()

        async def load_cogs(self) -> None:
            files = [
                f
                for f in os.listdir(f"{DIRS.PY}/extensions")
                if os.path.isfile(os.path.join(f"{DIRS.PY}/extensions", f))
            ]
            for file in files:
                try:
                    await self.load_extension(
                        f"extensions.{file.replace('.py', '')}"
                    )  # can we switch this back to nested strings in python 3.12?
                    print("    > Loaded cog!")
                except Exception as exc:
                    self.logger.error(
                        f"extensions.{file.replace('.py', '')} failed to load!",
                        exc_info=exc,
                    )
                    print(
                        f"----------\n> extensions.{file.replace('.py', '')} failed to load:"
                    )
                    traceback.print_exception(exc)
                    print("----------")

            print(
                f"----------\n{COLORS.BOLD}{self.user.name}#{self.user.discriminator} ({self.user.id}) is now connected and ready!{COLORS.RESET}"
            )

        async def reload_cogs(self) -> None:
            files = [
                f
                for f in os.listdir(f"{DIRS.PY}/extensions")
                if os.path.isfile(os.path.join(f"{DIRS.PY}/extensions", f))
            ]
            for file in files:
                try:
                    await self.reload_extension(
                        f"extensions.{file.replace('.py', '')}"
                    )  # can we switch this back to nested strings in python 3.12?
                    print("    > Loaded cog!")
                except commands.errors.ExtensionNotLoaded:
                    await self.load_extension(f"extensions.{file.replace('.py', '')}")
                    print("    > Loaded cog!")
                except Exception as exc:
                    self.logger.error(
                        f"extensions.{file.replace('.py', '')} failed to reload!",
                        exc_info=exc,
                    )
                    print(
                        f"----------\n> extensions.{file.replace('.py', '')} failed to reload:"
                    )
                    traceback.print_exception(exc)
                    print("----------")

            print(f"----------\n{COLORS.BOLD}Cogs have been reloaded!{COLORS.RESET}")

        async def setup_hook(self) -> None:
            print("Launching [issu]bot...")
            runner = asyncio.create_task(self.run_once_when_ready())
            runner.add_done_callback(self.error_handler)

    class HelpCommand():
        pass

    def __init__(self) -> None:
        self.default_bot = {
            "activity": None,
            "allowed_mentions": discord.AllowedMentions.none(),
            "command_prefix": "!",
            "description": "A Discord bot.",
            "help_command": commands.DefaultHelpCommand(),
            "intents": discord.Intents.all(),
            "case_insensitive": False,
        }
        self.bot_settings = json.load(open(f"{DIRS.JSON}/bot_settings.json"))
        self.owner_id = int(os.environ["OWNER_ID"].replace('"', ""))

    @classmethod
    def check_prefixes(self, prefixes: list | None = ["@"]) -> any:
        prefix_mention, other_prefixes = False, False

        for index, prefix in enumerate(prefixes):
            if prefix == "@":
                prefix_mention = True
                prefixes.pop(index)
            elif prefix_mention and other_prefixes:
                break
            else:
                other_prefixes = True

        if prefix_mention and other_prefixes:
            return commands.when_mentioned_or(*prefixes)
        elif prefix_mention:
            return commands.when_mentioned
        elif other_prefixes:
            return prefixes

    def add_commands(self, bot: commands.Bot):
        @bot.command(aliases=['reload', 'reload_extensions'])
        @commands.is_owner()
        async def reload_cogs(ctx):
            '''Reloads all extensions.
            '''
            await ctx.reply("Reloading extensions!")
            try:
                return await bot.reload_cogs()
            except Exception as exc:
                print(exc)
        
        @bot.command(aliases=['restart', 'reset', 'shutdown', 'stop'])
        @commands.is_owner()
        async def close(ctx):
            """Stops the bot. If functioning properly, it should automatically reboot and come back online.
            """

            await ctx.reply("Bot is shutting down...")
            await bot.change_presence(status=discord.Status.idle)
            await bot.close()

    def create_bot(self, use_default: bool | None = False) -> commands.Bot:
        set_dict = self.default_bot

        if not use_default:
            set_dict["activity"] = craft.activity(
                random.choice(self.bot_settings["activities"])
            )
            set_dict["allowed_mentions"] = craft.mentions(
                self.bot_settings["allowed_mentions"]
            )
            set_dict["command_prefix"] = self.check_prefixes(
                self.bot_settings["command_prefix"]
            )
            set_dict["description"] = self.bot_settings["description"]
            set_dict["case_insensitive"] = self.bot_settings["case_insensitive"]
            #set_dict["help_command"] = self.HelpCommand()

        bot = self.Bot(
            activity=set_dict["activity"],
            allowed_mentions=set_dict["allowed_mentions"],
            command_prefix=set_dict["command_prefix"],
            description=set_dict["description"],
            help_command=set_dict["help_command"],
            intents=set_dict["intents"],
            case_insensitive=set_dict["case_insensitive"],
            owner_id=self.owner_id,
        )

        self.add_commands(bot)

        return bot

import logging, logging.handlers

class log_handler:
    @classmethod
    def create_logging(self) -> None:
        logger = logging.getLogger("discord")
        logger.setLevel(logging.DEBUG)
        logging.getLogger("discord.http").setLevel(logging.INFO)

        handler = logging.handlers.RotatingFileHandler(
            filename=f"{DIRS.LOGGING}/discord.log",
            encoding="utf-8",
            maxBytes=32 * 1024 * 1024,
            backupCount=5,
        )
        dt_fmt = "%Y-%m-%d %H:%M:%S"
        formatter = logging.Formatter(
            "[{asctime}] [{levelname}] {name}: {message}", dt_fmt, style="{"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)


import requests


class version_handler:
    @classmethod
    def compare(
        self,
        current_ver: str | None = "Unknown",
        latest_ver: str | None = "Unknown",
        name: str | None = "None",
    ) -> None:
        print(
            f"Local {name} installation version: {COLORS.YELLOW+COLORS.BOLD+current_ver}"
        )
        print(
            f"{COLORS.RESET}Latest {name} installation: {COLORS.YELLOW+COLORS.BOLD+latest_ver}"
        )

        if latest_ver == "Unknown":
            print(
                f"{COLORS.UNDERLINE}Your {name} installation is potentially outdated, but the latest version could not be checked."
            )
            actions._sleep(2)
        elif latest_ver != current_ver and latest_ver != "Unknown":
            print(
                f"{COLORS.RED+COLORS.UNDERLINE}Your {name} installation IS OUTDATED! Consider updating it."
            )
            actions._sleep(2)
        else:
            print(f"{COLORS.GREEN}Your {name} installation is up-to-date!")
            actions._sleep(0.2)

        print(f"{COLORS.RESET}------------------")

    @classmethod
    def check_version(self) -> None:
        comparisons = {
        "Python": [
            platform.python_version(),
            "https://endoflife.date/api/python.json",
        ],
        "discord.py": [
            discord.__version__,
            "https://pypi.org/pypi/discord.py/json",
        ],
        "ro.py": [
            roblox.__version__,
            "https://pypi.org/pypi/roblox/json",
        ]
        }
        actions.clear()

        for comparison in comparisons.items():
            current_version = comparison[1][0]
            try:
                (r := requests.get(comparison[1][1])).raise_for_status()

                name = comparison[0]

                match (name):
                    case "Python":
                        latest_version = r.json()[0]["latest"]
                    case _:
                        try:
                            latest_version = list(json.loads(r.text)["releases"].keys())[-1]
                        except:
                            latest_version = "Unknown"
            except:
                latest_version = "Unknown"

            self.compare(current_version, latest_version, name)