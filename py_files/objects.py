import os, logging, traceback, sys, asyncio, io, json
import issutilities.craft as craft, issutilities.directories as directories, issutilities.colors as COLORS
import discord, discord.utils as utils
from discord.ext import commands
from typing import Callable, Awaitable, Any, cast

class Bot(commands.Bot):
    def __init__(self, *args, **kwargs) -> None: # Overridden
        super().__init__(*args, **kwargs)
        self._BotBase__cogs: Any = commands.core._CaseInsensitiveDict()
        
        self.all_activities: list[discord.Activity] = kwargs.get("all_activities", [])
        self.startup_notifs: dict[str, str] = kwargs.get("startup_notifs", {})
        self.DIRS: directories.DJISSU | directories.ISSUBOT = directories.ISSUBOT() if kwargs.get("botname") == "issubot" else directories.DJISSU()

        # rbxtoken = os.getenv("ROBLOX_TOKEN", "").replace('"', "")

        # self.roblox_client = roblox.Client(rbxtoken)        
        self.logger: logging.Logger = logging.getLogger("discord")
        
        self.owner: discord.User
        
        self.craft_this: craft.with_HTTP

        self.user: discord.User

    @staticmethod
    def __print_with_divider(text: str | None = None, with_timestamp: bool | None = True):
        print(f"---{f" {utils.utcnow()} " if with_timestamp else "-" * 34}{"--" * 6}{f"\n{text}" if text else ""}")

    def __get_all_extensions(self) -> list[str]:
        return [
                extension_file.replace(".py", "")
                for extension_file in os.listdir(f"{self.DIRS.PY}/extensions")
                if os.path.isfile(os.path.join(f"{self.DIRS.PY}/extensions", extension_file))
            ]

    def timer_cache(self, timer_id: str, action: str | None = "get", next_timestamp: int | float | None = None) -> int | float | None:
        next_timestamp = next_timestamp if next_timestamp else utils.utcnow().timestamp()

        with open(f"{self.DIRS.JSON}/next_iter.json", mode="r") as f:
            timers: dict[str, int | float] = json.load(f)

            match action:
                case "set":
                    timers[timer_id] = next_timestamp
                case "remove" | "delete":
                    timers.pop(timer_id)
                case _:
                    return timers.get(timer_id, 0)
              
        with open(f"{self.DIRS.JSON}/next_iter.json", mode="w") as f:
            json.dump(timers, f)

    async def base_error_handler(self, event: str, exception: BaseException, *args, **kwargs) -> None:
        if self.is_ready() and self.owner:
            exc_str = "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))
            exc_file = discord.File(fp=io.BytesIO(exc_str.encode("utf-8")), filename="exception.txt")

            await self.owner.send(file=exc_file)

        error_message = f"An error with {event} occurred: {exception}"

        self.logger.error(error_message, exc_info=exception)

        self.__print_with_divider(f"{error_message}\nargs: {args}\nkwargs: {kwargs}")
        traceback.print_exception(exception)

    async def on_error(self, event: str, *args, **kwargs) -> None:  # Overridden
        exc = cast(BaseException, sys.exc_info()[1])
        await self.base_error_handler(event, exc, *args, **kwargs)
        
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:  # Overridden
        if hasattr(ctx, 'error_handled'):
            return
        
        await self.base_error_handler(f"`{ctx.command.name if ctx.command else "Bot"}`{f"/**{ctx.invoked_with}**" if ctx.invoked_with else ""}", error, ctx.args)

        await ctx.reply(f"A little birdie told me that something went wrong. Well, idk how to deal with it so I'mma let {self.owner.mention if self.owner else "@issu"} take care of it. Here's some info:\n- Error: {error}\n- Args: {ctx.args}")

        # TODO: Customize this and make into embed!

    async def run_once_when_ready(self) -> None:
        await self.wait_until_ready()
        self.owner = cast(discord.User, self.get_user(self.owner_id or 0))
        await self.load_extensions()
        self.__print_with_divider(f"{COLORS.BOLD}{self.user.name}#{self.user.discriminator} ({self.user.id}) is now connected and ready!{COLORS.RESET}")

        if self.owner:
            startup_title = "# Startup Checks\n- "
            content_body = "\n- ".join(f"`{key}` {val}" for key, val in sorted(self.startup_notifs.items()))

            await self.owner.send(f"{startup_title}{content_body}")

    async def setup_hook(self) -> None:  # Overridden
        def setup_done_callback(task: asyncio.Task) -> None:
            exc = task.exception()
            if exc:
                asyncio.create_task(self.base_error_handler("setup_hook", exc))

        self.__print_with_divider(f"{COLORS.BOLD}Launching {self.user.name}...{COLORS.RESET}")
        runner = asyncio.create_task(self.run_once_when_ready())
        runner.add_done_callback(setup_done_callback)

    async def manage_extensions(self, action: str, coro: Callable[[str], Awaitable[None]], extensions: list[str] | None = None) -> None:
        action = action.capitalize()
        
        if not extensions:
            self.__print_with_divider(f"{COLORS.BOLD}{action} extensions...{COLORS.RESET}")

            extensions = self.__get_all_extensions()

        for extension in extensions:
            extension_name = f"extensions.{extension}"
            print(f"> {action} {extension_name}...")

            try:
                await coro(extension_name)
            except (commands.ExtensionAlreadyLoaded, commands.ExtensionNotLoaded):
                self.__print_with_divider(f"Extension {extension_name} attempted to set extension state to its current state.\nAction: {action}")
            except Exception as exc:
                await self.base_error_handler(f"manage_extensions ({action.lower()})/{extension_name}", exc)

            print(f"> {action} for {extension_name} finished.")

        if not extensions:
            self.__print_with_divider(f"{COLORS.BOLD}Extensions are done {action.lower()}!{COLORS.RESET}")

    async def load_extensions(self, extensions: list[str] | None = None) -> None:
        await self.manage_extensions("loading", self.load_extension, extensions)

    async def reload_extensions(self, extensions: list[str] | None = None) -> None:
        await self.manage_extensions("reloading", self.reload_extension, extensions)

    async def unload_extensions(self, extensions: list[str] | None = None) -> None:
        await self.manage_extensions("unloading", self.unload_extension, extensions)

    def run(self, token: str, *ignore: Any, **this: Any) -> None: # Overridden
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
        
class HelpCommand(commands.DefaultHelpCommand):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
