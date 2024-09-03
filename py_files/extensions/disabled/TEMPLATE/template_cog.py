# Template (Cog Version)
from discord.ext import commands
import os

# Rename this file! This becomes the cog's name.
name = (os.path.basename(__file__)).replace(".py", "")

# Describe what your cog does!
description = "An amazing cog!"


class Cog(commands.Cog, name=name, description=description):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        # Define cog variables here.
        # If you need to interact with the bot, use self.bot

    async def cog_load(self):
        pass
        # If you need something to occur when the bot loads the cog, do it here.
        # This is perfect for any async functions that can't be run in __init__.

    async def cog_unload(self) -> None:
        pass
        # If there is cleanup that needs to occur when the cog is unloaded, do it here.

    # define any function, listener, or command here.
    # For most items, Cog.[object] or commands.[object] instead of bot.[object]


# setup() and teardown() are required.
async def setup(bot):
    await bot.add_cog(Cog(bot), override=True)

    # If you want to interact with the bot, you can get
    # a reference to it from here.


async def teardown(bot):
    await bot.remove_cog(name)

    # Any cleanup that is required can be done here.
