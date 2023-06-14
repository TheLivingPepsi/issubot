import discord
from discord.ext import commands
import os
import json
import random
import logging
from handlers.utilities_handler import DIRS, craft_file, craft_files

name = (os.path.basename(__file__)).replace(".py", "")
logger = logging.getLogger("discord")


class Cog(commands.Cog, name=name):
    def __init__(self, bot):
        self.bot = bot
        self.responses = json.load(
            open(DIRS["json"] + "\\auto_responses.json", encoding="utf8")
        )
        self.punctuation = ".,:;/-@\"'!?\–\—•₽¥€¢£₩§”“„»«…¿¡\\’‘`$()_"

    async def cog_command_error(self, ctx, error):
        print(
            f"An error occurred in extensions.{name} / #{ctx.channel.name} ({ctx.channel.id}) | {error}\nMessage content:\n{ctx.message.content}"
        )
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

        if len(images) >= 1 and images[0] is not None:
            if len(images) == 1:
                d_file = await craft_file(images[0])
            else:
                d_files = await craft_files(images)
        else:
            d_file = None
            d_files = None

        await message.reply(content=content, file=d_file, files=d_files)

    @commands.is_owner()
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        for response in self.responses:
            for trigger in response["triggers"]:
                phrase = trigger["phrase"]

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
                        "".join(
                            c
                            for c in word
                            if c.isalpha() or c.isnumeric() or c.isspace()
                        )
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
                        respond = phrase in split
                    case 2:
                        respond = phrase in msg
                    case _:
                        respond = False

                if respond:
                    # add embed support?
                    # add channel filters so that it won't write messages/images in certain channels
                    await self.create_response(response, message)
                    break


async def setup(bot):
    print(f'> Loading cog "extensions.{name}"...')
    await bot.add_cog(Cog(bot), override=True)


async def teardown(bot):
    print(f'> Unloading cog "extensions.{name}"...')
    await bot.remove_cog(name)
