import os, discord
from discord.ext import commands
from discord import utils
from datetime import datetime

name = (os.path.basename(__file__)).replace(".py", "")

class Schemas:
    def __init__(self):
        self.languages = {
            **dict.fromkeys(["de", "german", "deutsch", "deutsche"], "de"), 
            **dict.fromkeys(["es", "spanish", "español", "espanol"], "es"),
            **dict.fromkeys(["fr", "french", "francais", "francaise", "français", "française"], "fr"),
            **dict.fromkeys(["it", "italian", "italiano", "italiana"], "it"),
            **dict.fromkeys(["pl", "polish", "polski", "polsku"], "pl"),
            **dict.fromkeys(["ru", "russian", "русский"], "ru"),
            **dict.fromkeys(["zh", "chinese", "中文"], "zh")
        }
        self.fallback = "en"
        self.datetime_format = "%Y-%m-%dT%H:%M:%SZ"

    def DiscordTimestamp(self, date: str | datetime) -> str:
        def get_date(date: str) -> datetime:
            return datetime.strptime(date, self.datetime_format)
        
        def get_timestamp(dt: datetime) -> str:
            return utils.format_dt(dt)
        
        try:
            if type(date) == str:
                date = get_date(date)

            return get_timestamp(date)
        except:
            return self.DiscordTimestamp(utils.utcnow())

    def PlanetNames(self, payload: list[dict], indent: int | None = 0) -> list[str]:
        # TODO: This could be merged with PlanetSchema, will have to see
        clamp = lambda x: max(0, min(round(x), 1)) 
        indent = clamp(indent)

        if len(payload) == 0:
            return [f"{" "*indent}- None!"]

        payload.sort(key=lambda x: x["name"])
        planets = []

        for planet in payload:
            planets.append(f"{" "*indent}- {planet["name"]}")

        return planets

    def WarSeasonOverview(self, payload: dict, latest: bool | None = False) -> dict:
        def get_seasons(seasons_payload: list[str]) -> list[str]:
            if len(seasons_payload) == 0:
                return ["- None!"]

            seasons = []

            for season in seasons_payload:
                season_text = f"- Season {season} {"**[CURRENT]**" if season == payload["current"] else ""}"
                seasons.append(season_text)

            return seasons

        title = latest and "# Current War Season" or "# War Seasons" 

        if latest:
            seasons = [f"- Season {payload["current"]}"]
        else:
            seasons = get_seasons(payload["seasons"])

        return {"title": title, "seasons": seasons}

    def PlanetSchema(self, payload: list[dict]) -> dict:
        pass

    def GlobalEventSchema(self, payload: list[dict], season: int, latest: bool | None = False, language: str | None = "en") -> list[dict]:  
        def get_effects(effects_payload: list) -> list:
            # TODO: When possible, try to use PlanetEffectSchema when it is mapped
            return ["- None!"]
        
        try:
            language = self.languages[language]
        except KeyError:
            language = self.fallback

        events = []

        title = f"# {"Latest War Event" if latest else "War Events"} of Season {season}"

        if len(payload) == 0:
            return {"title": title, "events": ["## None!"]}

        payload.sort(key=lambda x: x["id"], reverse=True)

        for i, event in enumerate(payload):
            subtitle = f"## Event {event["id"]}: {event["title"]}"
            faction = f"> **Affected faction**\n- {event["race"]}"
            planets = f"> **Remaining Involved Planets**\n{"\n".join(self.PlanetNames(event["planets"], 0))}"
            effects = f"> **Event Effects**\n{"\n".join(get_effects(event["effects"]))}"
            description = f"> **Description**\n{event["message"][language]}"

            events.append({"subtitle": subtitle, "faction": faction, "planets": planets, "effects": effects, "description": description})

            if latest and i == 0:
                break

        return {"title": title, "events": events}

    def HomeWorldSchema(self, payload: list[dict]) -> dict:
        def get_homeworlds(homeworlds_payload: dict) -> list:
            homeworlds = []

            for homeworld in homeworlds_payload:
                race = f"- Faction: {homeworld["race"]}"
                planets = self.PlanetNames(homeworld["planets"], 1)

            homeworlds.append({"race": race, "planets": planets})

            return homeworlds
        
        subtitle = f"## Homeworlds"
        homeworlds = get_homeworlds(payload)

        return {"subtitle": subtitle, "homeworlds": homeworlds}

    def WarInfoSchema(self, payload: dict) -> dict:
        title = f"# War Season {payload["war_id"]}"
        start_date = self.DiscordTimestamp(payload["start_date"])
        end_date = self.DiscordTimestamp(payload["end_date"])

        duration = f"## {start_date} - {end_date}"
        min_client_ver = f"## Required Client Version\n- {payload["minimum_client_version"]}+"
        homeworlds = self.HomeWorldSchema(payload["home_worlds"])
    
        return {"title": title, "duration": duration, "min_client_ver": min_client_ver, "homeworlds": homeworlds}
    
    # TODO: get all the json error schemas and make an error checker


class Cog(commands.Cog, name=name, description=""):
    def __init__(self, bot):
        self.bot = bot
        self.sources = ["http://localhost:4000/", "https://helldivers-2.fly.dev/"]
        self.latest_keywords = ["current", "latest", "now"]
        self.Schemas = Schemas()

    async def cog_load(self):
        print(f"    > extensions.{self.__cog_name__} has loaded!")

    async def cog_unload(self) -> None:
        print(f'> Unloading cog "extensions.{self.__cog_name__}"...')

    async def parse(self, to_parse: str | None = "") -> tuple:
        for source in self.sources:
            try:
                async with self.bot.craft_this.session.get(
                    f"{source}api/{to_parse}"
                ) as resp:
                    json = await resp.json()

                    return json, [resp.status, resp.reason]
            except:
                continue
            
    async def get_current_season(self, message: discord.Message) -> tuple:
        (parsed, status) = await self.parse()
            
        match status[0]:
            case 200:
                return parsed["current"], True
            case _:
                await message.edit(content=f"Something went wrong. {" ".join(status)}", allowed_mentions=discord.AllowedMentions.all())
                return None, False

    @commands.group(aliases=["hd", "hd2", "helldivers"], invoke_without_command=True)
    async def helldivers2(self, ctx: commands.Context, arg_1: int | str | None = "all", arg_2: str | None = None):
        try:
            war_id = int(arg_1)
            
            if arg_2 is not None:
                return await ctx.invoke(self.bot.get_command("hd2 events"), war_id, arg_2)

            await ctx.invoke(self.bot.get_command("hd2 info"), war_id)
        except ValueError:
            pass

        await ctx.invoke(self.bot.get_command("hd2 wars"), arg_1)

    @helldivers2.command(aliases=["seasons"])
    async def wars(self, ctx, view: str | None = "all"):
        """Gets all available war seasons by id."""
        get_latest = view.lower() in self.latest_keywords

        message = await ctx.reply(f"Getting {"current war season" if get_latest else "all war seasons"}...", mention_author=False)

        (parsed, status) = await self.parse()

        match status[0]:
            case 200:
                text = self.Schemas.WarSeasonOverview(parsed, get_latest)
                text["note_1"] = ("> - For a war season's events, use `p!hd events [season]`")
                text["note_2"] = ("> - For more information on a war season, use `p!hd info [season]`")
                parsed_string = f"""{text["title"]}
                {"\n".join(text["seasons"])}

                {text["note_1"]}
                {text["note_2"]}
                """
           
                return await message.edit(content=parsed_string, allowed_mentions=discord.AllowedMentions.all())
            case _:
                return await message.edit(content=f"Unable to get the seasons. {" ".join(status)}", allowed_mentions=discord.AllowedMentions.all())

    @helldivers2.command()
    async def events(self, ctx, season: int | None = None, view: str | None = "all", language: str | None = "en"):
        no_season = season == None
        get_latest = view.lower() in self.latest_keywords

        message = await ctx.reply(f"Getting {"the latest war event" if get_latest else "war events"} for {"the current season" if no_season else f"Season {season}"}...", mention_author=False)

        if no_season:
            (season, success) = await self.get_current_season(message)

            if not success:
                return
        
        (parsed, status) = await self.parse(f"{season}/events{"/latest" if get_latest else ""}")

        match status[0]:
            case 200:
                parsed = [parsed] if get_latest else parsed
                text = self.Schemas.GlobalEventSchema(parsed, season, get_latest, language)
                
                def get_subparsed_message(payload: dict) -> str:
                    subparsed_message = f"{payload["subtitle"]}\n{payload["description"]}\n\n{payload["faction"]}\n\n{payload["planets"]}\n\n{payload["effects"]}"

                    return subparsed_message

                parsed_message = f"""{text["title"]}
                {"\n\n".join([get_subparsed_message(event) for event in text["events"]])}
                """

                return await message.edit(content=parsed_message, allowed_mentions=discord.AllowedMentions.all())
            case _:
                return await message.edit(content=f"Unable to get the events. ({status[0]} {status[1]})", allowed_mentions=discord.AllowedMentions.all())

    @helldivers2.command(aliases=["info"])
    async def information(self, ctx, season: int | None = None):
        had_no_season = season == None
        message = await ctx.reply(f"Getting war info for {f"the current season" if had_no_season else f"Season {season}"}...", mention_author=False)

        if not season:
            (season, success) = await self.get_current_season(message)

            if not success:
                return
            
        (parsed, status) = await self.parse(f"{season}/info")

        match status[0]:
            case 200:
                text = self.Schemas.WarInfoSchema(parsed)
                parsed_message = "Currently unavailable!"

                return await message.edit(content=parsed_message, allowed_mentions=discord.AllowedMentions.all())
            case _:
                return await message.edit(content=f"Unable to get season info. ({status[0]} {status[1]})", allowed_mentions=discord.AllowedMentions.all())

    

async def setup(bot):
    print(f'> Loading cog "extensions.{name}"...')
    await bot.add_cog(Cog(bot), override=True)


async def teardown(bot):
    print(f'    > Cog "extensions.{name}" has unloaded.')
    await bot.remove_cog(name)
