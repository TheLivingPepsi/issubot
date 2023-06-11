import discord
from datetime import datetime
import os
import time

class COLORS: # add more colors soon
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
    '''
    TODO: Gotta make assets work. I mean. We should make it work soon
    https://discord.com/developers/docs/reference#image-formatting


    We could also make activity more fleshed out. it's not that huge of a feature, but we can later.
    '''
    try:
        if properties == None:
            raise TypeError("dict not provided")
        
        match(properties["type"]):
            case "Playing":
                activity = discord.Game(
                    name = properties["name"],
                    start = datetime.fromtimestamp(properties["start"]) if properties["start"] is not None else None,
                    end = datetime.fromtimestamp(properties["end"]) if properties["end"] is not None else None
                )
            
            case "Streaming":
                activity = discord.Streaming(
                    name = properties["name"] if properties["name"] is not None else "something",
                    url = properties["url"],
                    platform = properties["platform"],
                    game = properties["game"]
                )
            
            case "Listening" | "Watching" | "Competing":
                activity = discord.Activity(
                    type = discord.ActivityType.competing if properties["type"] == "Competing" else discord.ActivityType.listening if properties["type"] == "Listening" else discord.ActivityType.watching,
                    name = properties["name"] if properties["name"] is not None else "something"
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
            everyone = properties["everyone"],
            users = properties["users"],
            roles = properties["roles"],
            replied_user = properties["replied_user"]            
        )
        
        return allowed_mentions
    except:
        # log error? add later as it's a dev error and the function is not bot-critical.
        return None

def clear():
    os.system('cls' if os.name == "nt" else 'clear'), print(COLORS.RESET, end="")

def sleep(x):
    time.sleep(x)

base = os.environ["BASEPATH"].replace("\"", "")

DIRS = {
"base": base,
"logging": base+"\\logging_files",
"py": base+"\\py_files",
"json": base+"\\json_files"
}