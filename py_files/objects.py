import os, roblox, logging, traceback, sys, asyncio
import issutilities.actions as do, issutilities.craft as craft,  issutilities.directories as directories, issutilities.colors as COLORS
from discord import utils
from discord.ext import commands

class Bot(commands.Bot):
    def __init__(self, *args, **kwargs) -> None: # Overridden
        super().__init__(*args, **kwargs)
        
        self.all_activities = kwargs.get("all_activities")
        self.startup_notifs = kwargs.get("startup_notifs")
        self.DIRS = kwargs.get("botname") == "issubot" and directories.ISSUBOT or directories.DJISSU

        # rbxtoken = os.environ["ROBLOX_TOKEN"].replace('"', "")

        # self.roblox_client = roblox.Client(rbxtoken)        
        self.logger = logging.getLogger("discord")
        
        self.owner = None

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

        formatted_exception = " ".join(traceback.format_exception(exception))

        exception_body = (f"{name}: {formatted_exception}")[:1990]
        alternative_exception_body = (f"{name}: {formatted_exception}")[:1987]

        trunacted_exception = f"```\n{f"{exception_body}" if len(exception_body) < len(formatted_exception) else f"{alternative_exception_body}..."}\n```"

        # TODO: make this an embed!

        jump_url = None

        if type(ctx) == commands.Context and ctx.message:
            message = await ctx.message.reply(
                f"An error with name {name} occurred: {exception}\n\nA full debug log was sent to <@{self.owner_id}>."
            )
            jump_url = message.jump_url

        if self.owner:
            owner_message = await self.owner.send(trunacted_exception)
        else:
            owner_message = None

        await do.sleep_async(1)
        if jump_url and owner_message:
            await owner_message.reply(f"Jump URL: {jump_url}")
        elif owner_message and type(ctx) == str:
            await owner_message.reply(f"Event name: {ctx}")

    async def on_error(self, event: str, *args, **kwargs) -> None:  # Overridden
        exc = sys.exc_info()[1]
        await self.handle_exception(exc, None, event)

    async def on_command_error(
        self, ctx: commands.Context, error: BaseException
    ) -> None:  # Overridden
        command_name = ctx and ctx.command and ctx.command.name or None
        await self.handle_exception(error, ctx, command_name)

    async def run_once_when_ready(self) -> None:
        await self.wait_until_ready()
        await self.load_cogs()
        self.print_divider()
        print(
            f"{COLORS.BOLD}{self.user.name}#{self.user.discriminator} ({self.user.id}) is now connected and ready!{COLORS.RESET}"
        )
        self.owner = self.get_user(self.owner_id)

        if self.owner:
            startup_title = "# Startup Checks\n- "
            content_body = "\n- ".join(f"`{key}` {val}" for key, val in sorted(self.startup_notifs.items()))

            await self.owner.send(f"{startup_title}{content_body}")
 
    def setup_done_callback(self, task: asyncio.Task) -> None:
        exc = task.exception()
        if exc:
            asyncio.create_task(self.handle_exception(exc, None, "Setup"))

    async def setup_hook(self) -> None:  # Overridden
        self.print_divider()
        print(f"{COLORS.BOLD}Launching {self.user.name}...{COLORS.RESET}")
        runner = asyncio.create_task(self.run_once_when_ready())
        runner.add_done_callback(self.setup_done_callback)

    async def load_cogs(self, cogs: list | None = None) -> None:
        if not cogs:
            self.print_divider()
            print(f"{COLORS.BOLD}Loading cogs...{COLORS.RESET}")

            cogs = [
                cog_file 
                for cog_file in os.listdir(f"{self.DIRS.PY}/extensions")
                if os.path.isfile(os.path.join(f"{self.DIRS.PY}/extensions", cog_file))
            ]

        for cog in cogs:
            try:
                cog_name = f"extensions.{cog.replace(".py", "")}"
                await self.load_extension(cog_name)
                print(f"> Loaded {cog_name}!")
            except Exception as exc:
                print(f"> Failed to load {cog}: {exc}")
                await self.handle_exception(exc, None, f"load_cogs: {cog}", True)

        print(f"\n{COLORS.BOLD}Cogs are done loading!{COLORS.RESET}")

    async def reload_cogs(self) -> None:
        self.print_divider()
        print(f"{COLORS.BOLD}Reloading cogs...{COLORS.RESET}")

        cogs = [
            cog_file 
            for cog_file in os.listdir(f"{self.DIRS.PY}/extensions")
            if os.path.isfile(os.path.join(f"{self.DIRS.PY}/extensions", cog_file))
        ]

        for cog in cogs:
            cog_name = f"extensions.{cog.replace(".py", "")}"

            try:
                await self.reload_extension(cog_name)
                print(f"> Reloaded {cog_name}!")
            except commands.errors.ExtensionNotLoaded:
                print(f"> Cog {cog} was not loaded, loading cog...")
                await self.load_cogs([cog])
            except Exception as exc:
                print(f"> Failed to load {cog}: {exc}")
                await self.handle_exception(exc, None, f"reload_cogs: {cog}", True)

        print(f"\n{COLORS.BOLD}Cogs are done reloading!{COLORS.RESET}")

    def run(self, token: str, *args: any, **kwargs: any) -> None: # Overridden
        async def runner():
            async with craft.with_HTTP() as ClientObject:
                async with self:
                    self.craft_this = ClientObject
                    await self.start(token, reconnect=True)

                    await self.craft_this.close()
                    await self.http.close()

        try:
            asyncio.run(runner())
        except KeyboardInterrupt:
            # nothing to do here
            # `asyncio.run` handles the loop cleanup
            # and `self.start` closes all sockets and the HTTPClient instance.
            return

class HelpCommand(commands.HelpCommand):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
