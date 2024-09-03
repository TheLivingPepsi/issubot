import os
import discord
from discord.ext import commands
import json
from issutilities import craft
import random
from typing import cast

name = (os.path.basename(__file__)).replace(".py", "")


class Cog(
    commands.Cog,
    name=" ".join([word.capitalize() for word in name.split("_")]),
    description="Commands for managing auto-responses",
):
    def __init__(self, bot):
        self.bot = bot
        self.responses: dict = json.load(
            open(f"{bot.DIRS.JSON}/auto_responses.json", encoding="utf8")
        )
        self.punctuation = ".,:;/-@\"'!?–—•₽¥€¢£₩§”“„»«…¿¡\\’‘`$()_"
        self.craft_this = craft.with_HTTP()
        self.craft_these = self.craft_this

    async def create_response(self, response: dict, message: discord.Message):
        response_settings = response["response"]
        replies = response_settings["replies"]
        reactions = response_settings["reactions"]
        images = response_settings["images"]

        if len(replies["content"]) > 0 and replies["content"][0] is not None:
            content = cast(str, random.choice(replies["content"]))
        else:
            content = None

        if len(images) >= 1 and images[0] is not None:
            if len(images) == 1:
                d_file = await self.craft_this.discord_file(images[0])
                d_files = None
            else:
                d_file = None
                d_files = await self.craft_these.files(images)
        else:
            d_file = None
            d_files = None

        await message.reply(content=content, file=d_file, files=d_files)  # type: ignore

        if len(reactions["emojis"]) > 0 and reactions["emojis"][0] is not None:
            if reactions["random"]:
                emojis_container = reactions["emojis"]
                while len(emojis_container) > 0:
                    await message.add_reaction(
                        removed := random.choice(emojis_container)
                    )
                    emojis_container.remove(removed)
            else:
                for emoji in reactions["emojis"]:
                    await message.add_reaction(emoji)

    def check_list1_in_list2(self, list1: list, list2: list):
        if not list1 or not list2:
            return False

        if list1 == list2:
            return True

        for i in range(len(list2) - len(list1) + 1):
            if list1 == list2[i : i + len(list1)]:
                return True

        return False

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id != self.bot.owner_id:
            return

        try:
            ctx = await self.bot.get_context(message)

            if message.author.bot or ctx.valid:
                return

            for response in self.responses.values():
                for trigger in response["triggers"]:
                    phrase = trigger["phrase"]
                    phrase_split = phrase.split()

                    if any(punc in phrase for punc in self.punctuation):
                        msg = message.clean_content.replace("\n", " ")
                        split = message.clean_content.split()
                    else:
                        msg = "".join(
                            c
                            for c in message.clean_content.replace("\n", " ")
                            if c.isalpha() or c.isnumeric() or c.isspace()
                        )
                        split = [
                            "".join(c for c in word if c.isalpha() or c.isnumeric())
                            for word in message.clean_content.split()
                        ]

                    if not trigger["case_sensitive"]:
                        phrase = phrase.lower()
                        msg = msg.lower()
                        split = [word.lower() for word in split]

                    match (trigger["wildcard"]):
                        case 0:
                            respond = phrase == msg
                        case 1:
                            respond = phrase in split or self.check_list1_in_list2(
                                phrase_split, split
                            )
                        case 2:
                            respond = phrase in msg
                        case 3:
                            respond = phrase == split[0]
                        case 4:
                            respond = phrase == split[-1]
                        case _:
                            respond = False

                    if respond:
                        await self.create_response(response, message)
                        break
        except Exception as exc:
            ctx = await self.bot.get_context(message)
            await self.cog_command_error(ctx, exc)

    @commands.command(aliases=["rr"])
    @commands.is_owner()
    async def reload_responses(self, ctx):
        self.responses: dict = json.load(
            open(f"{self.bot.DIRS.JSON}/auto_responses.json", encoding="utf8")
        )
        await ctx.reply("Reloaded!")


async def setup(bot):
    await bot.add_cog(Cog(bot), override=True)


async def teardown(bot):
    await bot.remove_cog(name)
