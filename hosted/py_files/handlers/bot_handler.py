import discord
from discord.ext import commands
import asyncio
import json
import random
from util import craft_activity, craft_mentions


class Bot(commands.Bot):
    async def run_once_when_ready(self):
        await self.wait_until_ready()
        print(
            f"{self.user.name}#{self.user.discriminator} ({self.user.id}) is now connected and ready!"
        )

    async def setup_hook(self):
        asyncio.create_task(self.run_once_when_ready())


def check_prefixes(prefixes: list | None = ["@"]):
    prefix_mention, other_prefixes = False, False

    for prefix in prefixes:
        if prefix == "@":
            prefix_mention = True
        elif prefix_mention and other_prefixes:
            break
        else:
            other_prefixes = True

    if prefix_mention and other_prefixes:
        return commands.when_mentioned_or(*prefixes[1:])
    elif prefix_mention:
        return commands.when_mentioned
    elif other_prefixes:
        return prefixes


def craft_help_command(properties: dict | None = None):
    """
    TODO: make custom help command.
    https://discordpy.readthedocs.io/en/latest/ext/commands/api.html#ext-commands-help-command
    """

    try:
        if not properties["default"]:
            help_command = commands.HelpCommand(
                show_hidden=properties["command"]["show_hidden"],
                verify_checks=properties["command"]["verify_checks"]
                # Hey i think we can do more values. We should look into it later
            )
        else:
            raise Exception("Default value needed.")
        return help_command
    except:
        # log error? I mean, we get a default one. this is good enough
        return commands.DefaultHelpCommand()


def create_bot(filepath: str | None = "default"):
    set_dict = {
        "activity": None,
        "allowed_mentions": discord.AllowedMentions.none(),
        "command_prefix": "!",
        "description": "A Discord bot.",
        "help_command": commands.DefaultHelpCommand(),
        "intents": discord.Intents.all(),
        "case_insensitive": False,
    }

    if filepath != "default":
        settings_file = json.load(open(filepath))

        set_dict["activity"] = craft_activity(
            random.choice(settings_file["activities"])
        )
        set_dict["allowed_mentions"] = craft_mentions(settings_file["allowed_mentions"])
        set_dict["command_prefix"] = check_prefixes(settings_file["command_prefix"])
        set_dict["description"] = settings_file["description"]
        set_dict["help_command"] = craft_help_command(settings_file["help_command"])
        set_dict["case_insensitive"] = settings_file["case_insensitive"]

    return Bot(
        activity=set_dict["activity"],
        allowed_mentions=set_dict["allowed_mentions"],
        command_prefix=set_dict["command_prefix"],
        description=set_dict["description"],
        help_command=set_dict["help_command"],
        intents=set_dict["intents"],
        case_insensitive=set_dict["case_insensitive"],
    )
