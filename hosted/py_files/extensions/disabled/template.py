# Template
from discord.ext import commands
import os

name = (os.path.basename(__file__)).replace(".py", "") # rename this file


class Cog(commands.Cog, name=name):
    def __init__(self, bot):
        self.bot = bot
        # define any variables here with self.[variablename]

    # define any listeners or commands here


async def setup(bot):
    print(f'> Loading cog "extensions.{name}"...')
    await bot.add_cog(Cog(bot), override=True)


async def teardown(bot):
    print(f'> Unloading cog "extensions.{name}"...')
    await bot.remove_cog(name)
