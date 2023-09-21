from discord.ext import commands, tasks
import os

name = (os.path.basename(__file__)).replace(".py", "")  # rename this file


class Cog(commands.Cog, name=name):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        print(f"    > extensions.{self.__cog_name__} has loaded!")

    async def cog_unload(self) -> None:
        print(f"    > extensions.{self.__cog_name__} Cog has unloaded.")

    def cog_unload(self):
        self.counter.cancel()

    @commands.command()
    @commands.is_owner()
    async def start(self, ctx):
        self.counter.start()

    @tasks.loop(hours=24)
    async def counter(self):
        channel = self.bot.get_channel(845299672705007646)  # channel ID goes here
        await channel.send("issu kinda short no cap")

    @counter.before_loop
    async def before_my_task(self):
        await self.bot.wait_until_ready()  # wait until the bot logs in

    @commands.command(aliases=["raise"])
    @commands.is_owner()
    async def raise_(self, ctx):
        raise commands.CommandError("Nah man")


async def setup(bot):
    print(f'> Loading cog "extensions.{name}"...')
    await bot.add_cog(Cog(bot), override=True)


async def teardown(bot):
    print(f'> Unloading cog "extensions.{name}"...')
    await bot.remove_cog(name)
