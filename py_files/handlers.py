import discord, roblox
import os, json, random, traceback, platform, sys
import asyncio, logging, logging.handlers, requests, contextlib

from discord.ext import commands
from issutilities import DIRS, craft, COLORS, actions


class bot_handler:
    class Bot(commands.Bot):
        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)
            rbxtoken = os.environ["TOK_rbxacc_hz"].replace('"', "")

            self.ro_client = roblox.Client(rbxtoken)
            self.logger = logging.getLogger("discord")
            self.error = os.environ["error_dispatch"].split(",")
            self.channel = None

        async def handle_exception(
            self, exc, event=None, ctx=None, send_only=False
        ) -> None:
            if not send_only:
                print("----------")
                self.logger.error("An error occurred", exc_info=exc)

            channel = (
                self.channel
                if self.channel
                else await self.fetch_channel(self.error[1])
            )
            if channel:
                await channel.send(
                    content=f"- **Command invocation/event:** `{event}`\n- **Invocation Message:** `{ctx.message.content if ctx else 'None'}`\n- **Error Message:** `{exc}`\n```{''.join(traceback.format_exception(exc))}```"
                )

        def error_handler(self, task: asyncio.Task) -> None:
            exc = task.exception()
            if exc:
                asyncio.create_task(self.handle_exception(exc, None))

        async def setup_hook(self) -> None:
            print("Launching [issu]bot...")
            runner = asyncio.create_task(self.run_once_when_ready())
            runner.add_done_callback(self.error_handler)

        async def on_error(self, event, *args, **kwargs) -> None:
            exc = sys.exc_info()[1]
            await self.handle_exception(exc, event)

        async def on_command_error(self, ctx, error) -> None:
            command_name = ctx.command.name if ctx and ctx.command else None
            await self.handle_exception(error, command_name, ctx)
            await ctx.reply(
                f"```An error occurred.```\nFor debugging purposes, here is a simplified list of details:\n- **Type:** `{type(error)}**\n- `Message`: **{error}**\n\n> *A more detailed debugger was also logged.*"
            )

        async def run_once_when_ready(self) -> None:
            await self.wait_until_ready()
            self.channel = await self.fetch_channel(self.error[1])
            await self.load_cogs()
            print(
                f"----------\n{COLORS.BOLD}{self.user.name}#{self.user.discriminator} ({self.user.id}) is now connected and ready!{COLORS.RESET}"
            )

        async def load_cogs(self) -> None:
            files = [
                f
                for f in os.listdir(f"{DIRS.PY}/extensions")
                if os.path.isfile(os.path.join(f"{DIRS.PY}/extensions", f))
            ]

            print("----------\nLoading cogs...")

            for file_ in files:
                try:
                    await self.load_extension(
                        f"extensions.{file_.replace('.py', '')}"
                    )  # can we switch this back to nested strings in python 3.12?
                    print("    > Loaded cog!")
                except Exception as exc:
                    self.logger.error(
                        f"extensions.{file_.replace('.py', '')} failed to load!",
                        exc_info=exc,
                    )
                    print(
                        f"----------\n> extensions.{file_.replace('.py', '')} failed to load:"
                    )
                    traceback.print_exception(exc)
                    await self.handle_exception(exc, "load_cogs", send_only=True)
                    print("----------")

            print(f"----------\n{COLORS.BOLD}Cogs have loaded!{COLORS.RESET}")

        async def reload_cogs(self) -> None:
            files = [
                f
                for f in os.listdir(f"{DIRS.PY}/extensions")
                if os.path.isfile(os.path.join(f"{DIRS.PY}/extensions", f))
            ]

            print("----------\nReloading cogs...")

            for file_ in files:
                try:
                    await self.reload_extension(
                        f"extensions.{file_.replace('.py', '')}"
                    )  # can we switch this back to nested strings in python 3.12?
                except commands.errors.ExtensionNotLoaded:
                    await self.load_extension(f"extensions.{file_.replace('.py', '')}")
                except Exception as exc:
                    self.logger.error(
                        f"extensions.{file_.replace('.py', '')} failed to reload!",
                        exc_info=exc,
                    )
                    print(
                        f"----------\n> extensions.{file_.replace('.py', '')} failed to reload:"
                    )
                    traceback.print_exception(exc)
                    await self.handle_exception(exc, "load_cogs", send_only=True)
                    print("----------")

            print(f"----------\n{COLORS.BOLD}Cogs have been reloaded!{COLORS.RESET}")

    class HelpCommand(commands.MinimalHelpCommand):
        class HelpEmbed(discord.Embed):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.timestamp = discord.utils.utcnow()
                self.set_footer(text="<> is required | [] is optional")
                self.color = discord.Color.blurple()

        def __init__(self):
            super().__init__(
                command_attrs={
                    "help": "The help command for the bot",
                    "aliases": ["commands"],
                }
            )

        async def command_callback(self, ctx, /, *, command=None) -> None:
            await self.prepare_help_command(ctx, command)

            bot = ctx.bot

            if command is None:
                mapping = self.get_bot_mapping()
                return await self.send_bot_help(mapping)

            # Check if it's a cog
            cog = bot.get_cog(command)
            if cog is not None or command.lower() == "general":
                return await self.send_cog_help(cog)

            maybe_coro = discord.utils.maybe_coroutine

            # If it's not a cog then it's a command.
            # Since we want to have detailed errors when someone
            # passes an invalid subcommand, we need to walk through
            # the command group chain ourselves.
            keys = command.split(" ")
            cmd = bot.all_commands.get(keys[0])
            if cmd is None:
                string = await maybe_coro(
                    self.command_not_found, self.remove_mentions(keys[0])
                )
                return await self.send_error_message(string)

            for key in keys[1:]:
                try:
                    found = cmd.all_commands.get(key)  # type: ignore
                except AttributeError:
                    string = await maybe_coro(
                        self.subcommand_not_found, cmd, self.remove_mentions(key)
                    )
                    return await self.send_error_message(string)
                else:
                    if found is None:
                        string = await maybe_coro(
                            self.subcommand_not_found, cmd, self.remove_mentions(key)
                        )
                        return await self.send_error_message(string)
                    cmd = found

            if isinstance(cmd, commands.Group):
                return await self.send_group_help(cmd)
            else:
                return await self.send_command_help(cmd)

        async def send(self, **kwargs):
            channel = self.get_destination()
            ctx = self.context
            if ctx:
                return await ctx.reply(**kwargs)
            await channel.send(**kwargs)

        async def send_bot_help(self, mapping):
            ctx = self.context
            embed = self.HelpEmbed(title=f"{ctx.me.display_name} Help")
            embed.set_thumbnail(url=ctx.me.display_avatar)
            usable = 0

            for (
                cog,
                commands,
            ) in mapping.items():
                if filtered_commands := await self.filter_commands(commands, sort=True):
                    amount_commands = len(filtered_commands)
                    usable += amount_commands
                    if cog:
                        name = f"{cog.qualified_name}"
                        description = f"{cog.description or 'No description'}"
                    else:
                        name = "General"
                        description = "General Bot Commands"

                    commands = (
                        f"- Do {ctx.clean_prefix}help {name} for a list of commands."
                    )

                    embed.add_field(
                        name=f"> {name} [{amount_commands}]",
                        value=f"{description}\n{commands}",
                        inline=False,
                    )

            embed.add_field(
                name="> Additional Help",
                value=f"- Use {ctx.clean_prefix}help [category] for more info on categories\n- Use {ctx.clean_prefix}help [command] for more info on commands",
                inline=False,
            )

            embed.description = (
                f"*[{len(ctx.bot.commands)} commands | {usable} usable]*"
            )

            await self.send(embed=embed)

        async def send_command_help(self, command):
            if not command.hidden:
                signature = self.get_command_signature(command)
                embed = self.HelpEmbed(
                    title=signature,
                    description=command.help or "No description was provided!",
                )
                ctx = self.context
                embed.set_thumbnail(url=ctx.me.display_avatar)

                embed.add_field(
                    name="Aliases",
                    value=f"`{' | '.join(command.aliases)}`",
                    inline=False,
                )

                if cog := command.cog:
                    embed.add_field(name="Category", value=cog.qualified_name)
                else:
                    embed.add_field(name="Category", value="General")

                can_run = "No"
                with contextlib.suppress(commands.CommandError):
                    if await command.can_run(self.context):
                        can_run = "Yes"

                embed.add_field(name="Usable", value=can_run)

                if command._buckets and (cooldown := command._buckets._cooldown):
                    embed.add_field(
                        name="Cooldown",
                        value=f"{cooldown.rate} per {cooldown.per:.0f} seconds",
                    )

                return await self.send(embed=embed)

            await self.command_not_found()

        async def send_help_embed(self, title, description, commands):
            embed = self.HelpEmbed(
                title=title, description=description or "No description was provided!"
            )
            ctx = self.context
            embed.set_thumbnail(url=ctx.me.display_avatar)

            if filtered_commands := await self.filter_commands(commands, sort=True):
                for command in filtered_commands:
                    embed.add_field(
                        name=f"> {self.get_command_signature(command)}",
                        value=command.help or "No description was provided!",
                        inline=False,
                    )

            await self.send(embed=embed)

        async def send_group_help(self, group):
            title = self.get_command_signature(group)
            await self.send_help_embed(title, group.help, group.commands)

        async def send_cog_help(self, cog):
            if cog:
                title = cog.qualified_name or "No"
                description = cog.description
                commands = cog.get_commands()
            else:
                title = "General"
                description = "General bot commands"
                commands = [
                    filtered_command
                    for filtered_command in await self.filter_commands(
                        dict(self.get_bot_mapping().items())[None], sort=True
                    )
                ]

            await self.send_help_embed(f"{title} Category", description, commands)

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

        return None

    def do_additional_setup(self, bot: commands.Bot):
        bot._BotBase__cogs = commands.core._CaseInsensitiveDict()
        bot.help_command = self.HelpCommand()

        @bot.command(aliases=["reload", "reload_extensions"])
        @commands.is_owner()
        async def reload_cogs(ctx):
            """Reloads all extensions."""
            await ctx.reply("Reloading extensions!")
            try:
                return await bot.reload_cogs()
            except Exception as exc:
                print(exc)

        @bot.command(aliases=["restart", "reset", "shutdown", "stop"])
        @commands.is_owner()
        async def close(ctx):
            """Stops the bot. If functioning properly, it should automatically reboot and come back online."""

            await ctx.reply("Bot is shutting down...")
            await bot.change_presence(status=discord.Status.idle)
            print("----------\nBot is shutting down...")
            await bot.close()

        @bot.command(aliases=["latency", "test"])
        async def ping(ctx):
            """Displays the bot's latency/ping."""
            bot_latency = round(self.bot.latency * 1000, 2)

            await ctx.reply(f"🏓 Pong!\n- Bot latency: {bot_latency}ms")

    def create_bot(
        self, use_default: bool | None = False, version: int | None = 0
    ) -> commands.Bot:
        bot_settings = json.load(open(f"{DIRS.JSON}/bot_settings_{version}.json"))
        set_dict = self.default_bot.copy()
        if not use_default:
            for key in self.default_bot.keys():
                try:
                    if key == "activity":
                        set_dict["activity"] = craft.activity(
                            random.choice(bot_settings["activities"])
                        )
                    elif key == "allowed_mentions":
                        set_dict["allowed_mentions"] = craft.mentions(
                            bot_settings["allowed_mentions"]
                        )
                    elif key == "command_prefix":
                        set_dict["command_prefix"] = self.check_prefixes(
                            bot_settings["command_prefix"]
                        )
                    if set_dict[key] is None:
                        raise
                except:
                    set_dict[key] == self.default_bot[key]

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

        self.do_additional_setup(bot)

        return bot


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
            ],
        }

        actions._sleep(3)
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
                            latest_version = list(
                                json.loads(r.text)["releases"].keys()
                            )[-1]
                        except:
                            latest_version = "Unknown"
            except:
                latest_version = "Unknown"

            self.compare(current_version, latest_version, name)
