import os, discord, json
from discord.ext import commands

name = (os.path.basename(__file__)).replace(".py", "")

class Cog(commands.Cog, name=name, description=""):
    def __init__(self, bot):
        self.bot = bot
        self.sources = ["http://localhost:4000/", "https://helldivers-2.fly.dev/"]

    async def cog_load(self):
        print(f"    > extensions.{self.__cog_name__} has loaded!")

    async def cog_unload(self) -> None:
        print(f'> Unloading cog "extensions.{self.__cog_name__}"...')

    async def parse(self, to_parse: str | None = "") -> dict | list:
        for source in self.sources:
            async with self.bot.craft_this.session.get(
                f"{source}api/{to_parse}"
            ) as resp:
                return await resp.json(), [resp.status, resp.reason]
            
    async def get_current_season(self, message) -> tuple | None:
        (parsed, status) = await self.parse()
            
        match status[0]:
            case 200:
                return parsed["current"], True
            case _:
                await message.edit(content=f"Something went wrong. {" ".join(status)}", allowed_mentions=discord.AllowedMentions.all())
                return None, False
            
    @commands.group(aliases=["hd", "hd2", "helldivers"], invoke_without_command=True)
    async def helldivers2(self, ctx):
        await self.bot.get_command("helldivers2 wars").invoke(ctx)

    @helldivers2.command(aliases=["seasons"])
    async def wars(self, ctx):
        """Gets all available war seasons by id."""
        message = await ctx.reply("Getting all war seasons...", mention_author=False)

        (parsed, status) = await self.parse()

        match status[0]:
            case 200:
                message_content = f"""# War Seasons
                {"\n".join([f"- {season} {"**[CURRENT]**" if season == parsed["current"] else ""}" for season in parsed["seasons"]])}

                > - For a war season's events, use `p!helldivers events [season]`
                > - For more information on a war season, use `p!helldivers info [season]`
                """
                return await message.edit(content=message_content, allowed_mentions=discord.AllowedMentions.all())
            case _:
                return await message.edit(content=f"Unable to get the seasons. {" ".join(status)}", allowed_mentions=discord.AllowedMentions.all())

    @helldivers2.command()
    async def events(self, ctx, season: int | None = None, view: str | None = "latest"):
        had_no_season = season == None
        message = await ctx.reply(f"Getting war events for {"the current season" if had_no_season else "Season {season}"}...", mention_author=False)

        if not season:
            (season, success) = await self.get_current_season(message)

            if not success:
                return
            
        (parsed, status) = await self.parse(f"{season}/events{"/latest" if view.lower() == "latest" else ""}")

        match status[0]:
            case 200:
                events = []

                parsed = [parsed] if view.lower() == "latest" else parsed
                
                for event in parsed:
                    split_title = event["title"].split("\n", 1)
                    title = f"## {split_title[0]}"
                    effects = f"> **Effects**\n{"\n".join([f"- {effect}" for effect in event["effects"]]) if len(event["effects"]) > 0 else "- None!"}"
                    description = f"> **Description**\n{event["message"]["en"] if len(event["message"]["en"]) > 0 else split_title[1] if len(split_title) > 1 else "None!"}"
                    event_text = f"{title}\n{effects}\n\n{description}\n"
                    events.append(event_text)

                parsed_message = f"# {"Latest Event" if view.lower() == "latest" else "Events"} of War Season {season}{f" (current season)" if had_no_season else ""}\n{"\n".join(events)}"

                return await message.edit(content=parsed_message, allowed_mentions=discord.AllowedMentions.all())
            case _:
                return await message.edit(content=f"Unable to get the events. {" ".join(status)}", allowed_mentions=discord.AllowedMentions.all())

    @helldivers2.command(aliases=["info"])
    async def information(self, ctx, season: int | None = None):
        had_no_season = season == None
        message = await ctx.reply(f"Getting info for war {f"the current season" if had_no_season else f"Season {season}"}...", mention_author=False)

        if not season:
            (season, success) = await self.get_current_season(message)

            if not success:
                return
            
        (parsed, status) = await self.parse(f"{season}/info")

        match status[0]:
            case 200:
                dumped_string = json.dumps(parsed, indent=2)

                if len(dumped_string) > 1986:
                    partitions = dumped_string[:1981].rpartition("\n")
                    max_length = len(partitions[2])
                    lines = len((dumped_string.replace(f"{partitions[0]}{partitions[1]}", "")).split("\n"))-2
                    new_line = f"[{lines} more lines...]"

                    if len(new_line) > max_length:
                        new_line = "[...]"

                    dumped_string = f"{partitions[0]}\n{new_line}"


                parsed_string = f"```json\n{dumped_string}\n```"

                return await message.edit(content=parsed_string, allowed_mentions=discord.AllowedMentions.all())
            case _:
                return await message.edit(content=f"Unable to get season info. {" ".join(status)}", allowed_mentions=discord.AllowedMentions.all())

async def setup(bot):
    print(f'> Loading cog "extensions.{name}"...')
    await bot.add_cog(Cog(bot), override=True)


async def teardown(bot):
    print(f'    > Cog "extensions.{name}" has unloaded.')
    await bot.remove_cog(name)
