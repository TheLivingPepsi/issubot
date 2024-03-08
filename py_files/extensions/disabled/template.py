# Template
from discord.ext import commands
import os

name = (os.path.basename(__file__)).replace(".py", "")  # rename this file


class Cog(commands.Cog, name=name, description=""):
    def __init__(self, bot):
        self.bot = bot
        # define any variables here with self.variablename = value

    async def cog_load(self):
        print(f"    > extensions.{self.__cog_name__} has loaded!")
        # If you need something to occur when the bot loads, write it here

    async def cog_unload(self) -> None:
        print(f"    > extensions.{self.__cog_name__} Cog has unloaded.")
        # If there is cleanup that needs to occur when the cog is unloaded, do it here

    # define any listeners or commands here


async def setup(bot):
    print(f'> Loading cog "extensions.{name}"...')
    await bot.add_cog(Cog(bot), override=True)


async def teardown(bot):
    print(f'> Unloading cog "extensions.{name}"...')
    await bot.remove_cog(name)
