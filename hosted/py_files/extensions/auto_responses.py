import os
import discord
from discord.ext import commands
import json
from utilities import DIRS, craft
import logging, logging.handlers, traceback
import random

name = (os.path.basename(__file__)).replace(".py", "")


class Cog(commands.Cog, name=name):
    def __init__(self, bot):
        self.bot = bot
        self.responses = json.load(
            open(f"{DIRS.JSON}\\auto_responses.json", encoding="utf8")
        )
        self.punctuation = ".,:;/-@\"'!?\–\—•₽¥€¢£₩§”“„»«…¿¡\\’‘`$()_"
        self.logger = logging.getLogger("discord")

    async def cog_command_error(self, ctx, error):
        print(
            f"----------\nAn error occurred in extensions.{name} / #{ctx.channel.name} ({ctx.channel.id}) | {error}\nMessage content:\n{ctx.message.content}"
        )
        traceback.print_exception(error)

        logging.error(
            f"An error occurred in extensions.{name} / #{ctx.channel.name} ({ctx.channel.id}) @ {ctx.message.jump_url}!",
            exc_info=error,
        )

    async def create_response(self, response: dict, message: discord.Message):
        response_settings = response["response"]
        replies = response_settings["replies"]
        reactions = response_settings["reactions"]
        images = response_settings["images"]

        if len(replies["content"]) > 0 and replies["content"][0] is not None:
            content = random.choice(replies["content"])
        else:
            content = None

        if len(images) >= 1 and images[0] is not None:
            if len(images) == 1:
                d_file = await craft.file(images[0])
            else:
                d_files = await craft.files(images)
        else:
            d_file = None
            d_files = None

        await message.reply(content=content, file=d_file, files=d_files)

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

            for response in self.responses:
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
                        case _:
                            respond = False

                    if respond:
                        await self.create_response(response, message)
                        break
        except Exception as exc:
            ctx = await self.bot.get_context(message)
            await self.cog_command_error(ctx, exc)


async def setup(bot):
    print(f'> Loading cog "extensions.{name}"...')
    await bot.add_cog(Cog(bot), override=True)


async def teardown(bot):
    print(f'> Unloading cog "extensions.{name}"...')
    await bot.remove_cog(name)
