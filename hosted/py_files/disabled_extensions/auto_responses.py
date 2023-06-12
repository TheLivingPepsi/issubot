### --- IMPORTS --- ###
import discord
from discord.ext import commands
import os
import json
import re
import random
from handlers.utilities_handler import DIRS, craft_file, craft_files

name = (os.path.basename(__file__)).replace(".py", "")

responses = json.load(open(DIRS["json"] + "\\auto_responses.json"))
punctuation = r".,:;/-@\"\'!?–—•₽¥€¢£₩§”“„»«…¿¡\\’‘`" + r"\$\(\)"


class Cog(commands.Cog, name=name):
    def __init__(self, bot):
        self.bot = bot

    async def create_response(self, response: dict, message: discord.Message):
        if (
            len(response["response"]["replies"]["content"]) > 0
            and response["response"]["replies"]["content"][0] is not None
        ):
            content = random.choice(response["response"]["replies"]["content"])

        if (
            len(response["response"]["reactions"]["emojis"]) > 0
            and response["response"]["reactions"]["emojis"][0] is not None
        ):
            if response["response"]["reactions"]["random"]:
                emojis_container = response["response"]["reactions"]["emojis"]
                while len(emojis_container) > 0:
                    await message.add_reaction(
                        removed := random.choice(emojis_container)
                    )
                    emojis_container.remove(removed)
            else:
                for emoji in response["response"]["reactions"]["emojis"]:
                    await message.add_reaction(emoji)

        if len(response["response"]["images"]) == 1:
            d_file = await craft_file(response["response"]["images"][0])
        elif len(response["response"]["images"]) > 1:
            d_files = await craft_files(response["response"]["images"])

        await message.reply(content=content, file=d_file, files=d_files)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        try:
            for response in responses:
                trigger = response["trigger"]
                wildcard = trigger["wildcard"]

                for phrase in trigger["phrases"]:
                    if any(punc in phrase for punc in punctuation):
                        msg = message.clean_content
                        split = message.clean_content.split()
                    else:
                        msg = re.sub(rf"[{punctuation}]", "", message.clean_content)
                        split = [
                            re.sub(rf"[{punctuation}]", "", word)
                            for word in message.clean_content.split()
                        ]

                    match (wildcard):
                        case 0:
                            respond = phrase == msg
                        case 1:
                            respond = phrase in msg
                        case 2:
                            respond = phrase in split

                    if respond:
                        # add embed support?
                        # add channel filters so that it won't write messages/images in certain channels
                        self.create_response(response, message)

        except:
            # log
            return


async def setup(bot):
    await bot.add_cog(Cog(bot), override=True)
    print(f'Loading cog "{name}".')


async def teardown(bot):
    await bot.remove_cog(name)
    print(f'Unloading cog "{name}".')
