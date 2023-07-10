import discord
import os
import time
import aiohttp, io
import asyncio
import platform


class COLORS:
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    RESET = "\033[0m"


class DIRS:
    BASE = os.environ["BASEPATH"].replace('"', "")
    LOGGING = f"{BASE}\\logging_files"
    PY = f"{BASE}\\py_files"
    JSON = f"{BASE}\\json_files"


class actions:
    @classmethod
    def clear(self) -> None:
        os.system("cls" if os.name == "nt" else "clear"), print(COLORS.RESET, end="")

    @classmethod
    def _sleep(self, x: int | float | None = 0) -> None:
        time.sleep(x)

    @classmethod
    async def sleep(self, x: int | float | None = 0) -> None:
        asyncio.sleep(x)

    @classmethod
    async def request_http(
        self, link: str | None = None
    ) -> aiohttp.ClientResponse | str:
        async with aiohttp.ClientSession() as session:
            async with session.get(link) as r:
                if r.status == 200:
                    return True, r
                else:
                    return False, f"Could not GET {link} | STATUS: {r.status}"


class craft:
    @classmethod
    def activity(self, properties: dict | None = None) -> discord.Activity | None:
        try:
            if properties == None:
                raise TypeError("dict not provided")

            match (properties["type"]):
                case "Playing":
                    activity = discord.Game(
                        name=properties["name"]
                        if properties["name"] is not None
                        else "something",
                    )

                case "Streaming":
                    activity = discord.Streaming(
                        name=properties["name"]
                        if properties["name"] is not None
                        else "something",
                        url=properties["url"]
                        if properties["url"] is not None
                        else "https://www.twitch.tv/thelivingpepsi",
                    )

                case "Listening" | "Watching" | "Competing":
                    activity = discord.Activity(
                        type=discord.ActivityType.competing
                        if properties["type"] == "Competing"
                        else discord.ActivityType.listening
                        if properties["type"] == "Listening"
                        else discord.ActivityType.watching,
                        name=properties["name"]
                        if properties["name"] is not None
                        else "something",
                    )

                case _:
                    raise ValueError("A key or value was not valid.")

            return activity
        except:
            return None

    @classmethod
    def mentions(
        self, properties: dict | None = None
    ) -> discord.AllowedMentions | None:
        try:
            if properties == None:
                raise TypeError("dict not provided")

            allowed_mentions = discord.AllowedMentions(
                everyone=properties["everyone"],
                users=properties["users"],
                roles=properties["roles"],
                replied_user=properties["replied_user"],
            )

            return allowed_mentions
        except:
            return None

    @classmethod
    async def _file(self, properties: dict | None = None) -> discord.File | None:
        try:
            if properties == None:
                raise TypeError("dict not provided")

            if properties["is_url"]:
                data = await self.file_from_url(properties["path"])
            else:
                with open(properties["path"], "rb") as fp:
                    data = fp

            if data == None:
                return None

            d_file = discord.File(data, properties["filename"])

            return d_file
        except:
            return None

    @classmethod
    async def files(self, files: list | None = None) -> list | None:
        try:
            return [await self.file(d_file) for d_file in files]
        except:
            return None

    @classmethod
    async def file_from_url(self, url: str | None = None) -> discord.File | None:
        success, resp = await actions.request_http(url)

        if success:
            data = io.BytesIO(await resp.read())
            return data
        return None


COMPARISONS = {
    "Python": [
        platform.python_version(),
        "https://endoflife.date/api/python.json",
    ],
    "discord.py": [
        discord.__version__,
        "https://pypi.org/pypi/discord.py/json",
    ],
}
