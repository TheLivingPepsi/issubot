import discord
from datetime import datetime


### --- Utilities --- ###
## -- Craft Discord Activity -- ##

def craft_activity(properties: dict = None):
    if properties == None:
        return None
    
    '''
    TODO: Gotta make assets work. I mean. We should make it work soon
    https://discord.com/developers/docs/reference#image-formatting
    '''

    match (properties["type"]):
        case 0: # Playing
            return discord.Game(
                name = properties["name"],
                start = datetime.fromtimestamp(properties["start"]) if properties["start"] is not None else None,
                end = datetime.fromtimestamp(properties["end"]) if properties["end"] is not None else None
            )
        case 1: # Streaming
            return discord.Streaming(
                name = properties["name"],
                url = properties["url"] if properties["url"] is not None else "https://www.youtube.com/TheLivingPepsi",
                platform = properties["platform"] if properties["platform"] is not None else None,
                game = properties["game"] if properties["game"] is not None else None
            )

        case _: # Listening/Watching/Competing
            return discord.Activity(
                type = properties["type"],
                name = properties["name"],
                state = properties["state"] if properties["state"] is not None else None,
                details = properties["details"] if properties["details"] is not None else None,
                start = datetime.fromtimestamp(properties["start"]) if properties["start"] is not None else None,
                end = datetime.fromtimestamp(properties["end"]) if properties["end"] is not None else None
            )

