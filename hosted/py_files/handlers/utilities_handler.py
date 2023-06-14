import discord
from datetime import datetime
import os
import time
import aiohttp, io


class COLORS:  # add more colors soon
    DISCORD_GREEN = ""
    DISCORD_RED = ""
    DISCORD_YELLOW = ""
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    RESET = "\033[0m"


def craft_activity(properties: dict | None = None):
    """
    TODO: Gotta make assets work. I mean. We should make it work soon
    https://discord.com/developers/docs/reference#image-formatting


    We could also make activity more fleshed out. it's not that huge of a feature, but we can later.
    """
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
        # log error? add later as it's a dev error and the function is not bot-critical.
        return None


def craft_mentions(properties: dict | None = None):
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
        # log error? add later as it's a dev error and the function is not bot-critical.
        return None


async def craft_file(properties: dict | None = None):
    try:
        if properties == None:
            raise TypeError("dict not provided")

        if properties["is_url"]:
            data = await get_file_from_url(properties["path"])
        else:
            with open(properties["path"], "rb") as fp:
                data = fp

        if data == None:
            return None

        d_file = discord.File(data, properties["filename"])

        return d_file
    except:
        # log error? add later as it's a dev error and the function is not bot-critical.
        return


async def craft_files(files: list | None = None):
    try:
        return [await craft_file(d_file) for d_file in files]
    except:
        # log error? add later as it's a dev error and the function is not bot-critical.
        return


async def get_file_from_url(url: str | None = None):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return None
            data = io.BytesIO(await resp.read())
            return data


def clear():
    os.system("cls" if os.name == "nt" else "clear"), print(COLORS.RESET, end="")


def sleep(x):
    time.sleep(x)


base = os.environ["BASEPATH"].replace('"', "")

DIRS = {
    "base": base,
    "logging": base + "\\logging_files",
    "py": base + "\\py_files",
    "json": base + "\\json_files",
}
