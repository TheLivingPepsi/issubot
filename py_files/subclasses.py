import os, roblox, logging, traceback, sys, asyncio, aiohttp
from discord import utils
from discord.ext import commands
from discord.ext.commands import errors
from issutilities.actions import CONSOLE as do
import issutilities.directories as directories
from issutilities.colors import ANSI as COLORS

class Bot(commands.Bot):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        
        self.all_activities = kwargs.get("all_activities")
        self.startup_notifs = kwargs.get("startup_notifs")
        self.DIRS = kwargs.get("botname") == "issubot" and directories.ISSUBOT or directories.DJISSU

        # rbxtoken = os.environ["ROBLOX_TOKEN"].replace('"', "")

        # self.roblox_client = roblox.Client(rbxtoken)
        self.aiohttp_client = aiohttp.ClientSession()

        self.logger = logging.getLogger("discord")
        self.bot = self

    def print_divider(self):
        print(f"--- {utils.utcnow()} {"--" * 6}")

    async def handle_exception(
        self,
        exception: BaseException,
        ctx: commands.Context | None = None,
        name: str | None = "",
        do_not_print: bool | None = False
    ) -> None:
        self.logger.error(f"An error occurred with name {name}", exc_info=exception)

        if not do_not_print:
            self.print_divider()
            traceback.print_exception(exception)

        owner = self.get_user(self.owner_id)

        exception_body = (f"{name}: {" ".join(traceback.format_exception(exception))}")[:1995]

        trunacted_exception = f"`{exception}...`"

        # TODO: make this an embed!

        jump_url = None

        if type(ctx) == commands.Context and ctx.message:
            message = await ctx.message.reply(
                f"An error with name {name} occurred: {exception}\n\nA full debug log was sent to <@{self.owner_id}>."
            )
            jump_url = message.jump_url

        owner_message = await owner.send(trunacted_exception)
        await do.sleep_async(1)
        if jump_url and owner_message:
            await owner_message.reply(f"Jump URL: {jump_url}")
        elif owner_message and type(ctx) == str:
            await owner_message.reply(f"Event name: {ctx}")

    async def close(self) -> None: # Overridden
        await self.aiohttp_client.close()
        await super().close()

    async def on_error(self, event: str, *args, **kwargs) -> None:  # Overridden
        exc = sys.exc_info()[1]
        await self.handle_exception(exc, None, event)

    async def on_command_error(
        self, ctx: commands.Context, error: BaseException
    ) -> None:  # Overridden
        command_name = ctx and ctx.command.name or None
        await self.handle_exception(error, ctx, command_name)

    async def run_once_when_ready(self) -> None:
        await self.wait_until_ready()
        await self.load_cogs()
        self.print_divider()
        print(
            f"{COLORS.BOLD}{self.user.name}#{self.user.discriminator} ({self.user.id}) is now connected and ready!{COLORS.RESET}"
        )

    def setup_done_callback(self, task: asyncio.Task) -> None:
        exc = task.exception()
        if exc:
            asyncio.create_task(self.handle_exception(exc, None, "Setup"))

    async def setup_hook(self) -> None:  # Overridden
        self.print_divider()
        print(f"Launching {self.user.name}...")
        runner = asyncio.create_task(self.run_once_when_ready())
        runner.add_done_callback(self.setup_done_callback)

    async def load_cogs(self, cogs: list | None = None) -> None:
        if not cogs:
            self.print_divider()
            print("Loading cogs...")

            cogs = [
                cog_file 
                for cog_file in os.listdir(f"{self.DIRS.PY}/extensions")
                if os.path.isfile(os.path.join(f"{self.DIRS.PY}/extensions", cog_file))
            ]

        for cog in cogs:
            try:
                await self.load_extension(f"extensions.{cog.replace(".py", "")}")
                print(f"> Loaded {cog}!")
            except Exception as exc:
                print(f"> Failed to load {cog}: {exc}")
                await self.handle_exception(exc, None, f"load_cogs: {cog}", True)

        if not cogs:
            print(f"\n{COLORS.BOLD}Cogs are done loading!{COLORS.RESET}")

    async def reload_cogs(self) -> None:
        self.print_divider()
        print("reloading cogs...")

        cogs = [
            cog_file 
            for cog_file in os.listdir(f"{self.DIRS.PY}/extensions")
            if os.path.isfile(os.path.join(f"{self.DIRS.PY}/extensions", cog_file))
        ]

        for cog in cogs:
            try:
                await self.reload_extension(f"extensions.{cog.replace(".py", "")}")
                print(f"> Reloaded {cog}!")
            except errors.ExtensionNotLoaded:
                print(f"> Cog {cog} was not loaded, loading cog...")
                self.load_cogs([cog])
            except Exception as exc:
                print(f"> Failed to load {cog}: {exc}")
                await self.handle_exception(exc, None, f"reload_cogs: {cog}", True)

        print(f"\n{COLORS.BOLD}Cogs are done reloading!{COLORS.RESET}")

class HelpCommand(commands.HelpCommand):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
