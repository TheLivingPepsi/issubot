import discord
from discord.ext import commands
import asyncio
import json
import random
from handlers.utilities_handler import craft_activity, craft_mentions, DIRS
import os
import logging


class CustomBot(commands.Bot):
    def error_handler(self, task: asyncio.Task):
        exc = task.exception()
        if exc:
            logging.error("ready task failed!", exc_info=exc)

    async def run_once_when_ready(self):
        await self.wait_until_ready()
        files = [
            f
            for f in os.listdir(DIRS["py"] + "\\extensions")
            if os.path.isfile(os.path.join(DIRS["py"] + "\\extensions", f))
        ]
        for file in files:
            try:
                await self.load_extension(
                    f"extensions.{file.replace('.py', '')}"
                )  # can we switch this back to nested strings in python 3.12?
            except commands.ExtensionNotFound:
                print(f"> Could not load extensions.{file.replace('.py', '')}!")
            except commands.ExtensionAlreadyLoaded:
                print(f"> extensions.{file.replace('.py', '')} was already loaded.")

        print(
            f"{self.user.name}#{self.user.discriminator} ({self.user.id}) is now connected and ready!"
        )

    async def setup_hook(self):
        print("Launching [issu]bot...")
        runner = asyncio.create_task(self.run_once_when_ready())
        runner.add_done_callback(self.error_handler)


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


def create_bot(filepath: str | None = "default", logger: logging.Logger | None = None):
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

    return CustomBot(
        activity=set_dict["activity"],
        allowed_mentions=set_dict["allowed_mentions"],
        command_prefix=set_dict["command_prefix"],
        description=set_dict["description"],
        help_command=set_dict["help_command"],
        intents=set_dict["intents"],
        case_insensitive=set_dict["case_insensitive"],
    )
