### --- IMPORTS --- ###
import discord
from discord.ext import commands
import os
from util import DIRS

### --- COG --- ###
name = (os.path.basename(__file__)).replace(".py", "")

class Cog(commands.Cog, name=name):
    def __init__(self, bot):
        self.bot = bot
        self.responses = DIRS["json"]+"\\auto_responses.json"

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

### --- EXTENSION MANAGEMENT --- ###
async def setup(bot):
    await bot.add_cog(Cog(bot), override=True)
    print(f"Loading cog \"{name}\".")

async def teardown(bot):
    await bot.remove_cog(name)
    print(f"Unloading cog \"{name}\".")