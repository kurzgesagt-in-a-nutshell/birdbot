import logging
import asyncio
import json
import re

import aiohttp

import demoji
import pymongo

import discord
from discord.ext import commands
from discord import app_commands

from app.utils import checks
from app.utils.config import Reference


class Misc(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger("Misc")
        self.bot = bot
        self.intro_db = self.bot.db.StaffIntros
        self.kgs_guild = None
        self.role_precendence = (
            915629257470906369,
            414029841101225985,
            414092550031278091,
            1058243220817063936,
            681812574026727471,
        )
        with open("config.json", "r") as f:
            self.config = json.load(f)

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info("Loaded Misc Cog")

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.nick == after.nick:
            return

        self.kgs_guild = self.bot.get_guild(Reference.guild)
        subreddit_role = discord.utils.get(self.kgs_guild.roles, id=Reference.Roles.subreddit_mod)
        if not after.top_role >= subreddit_role:
            return

        intro = self.intro_db.find_one({"_id": before.id})
        intro_channel = self.kgs_guild.get_channel(
            Reference.Channels.intro_channel
        )
        msg = await intro_channel.fetch_message(intro["message_id"])
        embed = msg.embeds[0]
        embed.set_author(name=after.display_name, icon_url=after.avatar.url)
        await msg.edit(embed=embed)

    @commands.Cog.listener()
    async def on_user_update(self, before, after):

        self.kgs_guild = self.bot.get_guild(Reference.guild)

        member = self.kgs_guild.get_member(before.id)
        if not member:
            return
        subreddit_role = discord.utils.get(self.kgs_guild.roles, id=Reference.Roles.subreddit_mod)
        if not member.top_role >= subreddit_role:
            return

        intro = self.intro_db.find_one({"_id": before.id})
        intro_channel = self.kgs_guild.get_channel(
            Reference.Channels.intro_channel
        )
        msg = await intro_channel.fetch_message(intro["message_id"])
        embed = msg.embeds[0]
        embed.set_author(name=member.display_name, icon_url=after.avatar.url)
        await msg.edit(embed=embed)



    @app_commands.command()
    @checks.devs_only()
    async def intro_modal(self, interaction: discord.Interaction):
        """
        Staff intro commands
        Usage: intro
        """        
        oldIntro = self.intro_db.find_one({"_id": interaction.user.id})
        await interaction.response.send_modal(introModal(oldIntro=oldIntro, bot = self.bot))


class introModal(discord.ui.Modal):
    """
    The modal UI for intro commands.
    """
    def __init__(self, oldIntro, bot):
        super().__init__(title="Introduce yourself!")
        self.oldIntro = oldIntro
        #we need to have the bot!
        self.bot = bot
        self.intro_db = bot.db.StaffIntros
        # require fields if intro is empty and set up placeholders/default values
        timezone_ph = bio_ph = image_ph = None
        timezone_default = bio_default = image_default = None
        if oldIntro:
            timezone_default  = oldIntro["tz_text"]
            bio_default = oldIntro["bio"]
            image_default = oldIntro["image"]
            required = False
            #we are doing this for error handling or in case the mongo entry remained incomplete
            if oldIntro["message_id"] == None:
                required = True
        else:
            timezone_ph = "The internet - UTC | GMT+0:00"
            bio_ph = "Hello! I'm Birdbot and I help run this server."
            image_ph = "https://cdn.discordapp.com/avatars/471705718957801483/cfcf7fbcdc9579d7f0606b014aa1ede8.png"
            required = True

        self.required = required
        
        self.timezone = discord.ui.TextInput(label='Enter your timezone.', style=discord.TextStyle.short, required=required, placeholder=timezone_ph, default = timezone_default, max_length=90)

        self.bio = discord.ui.TextInput(label='Enter your bio.', style=discord.TextStyle.paragraph, required=required, placeholder=bio_ph, default=bio_default)

        self.image = discord.ui.TextInput(label='Enter the image link for your personal bird.', style=discord.TextStyle.short, required=required, placeholder=image_ph, default=image_default)

        self.add_item(self.timezone)
        self.add_item(self.bio)
        self.add_item(self.image)

    async def on_submit(self, interaction: discord.Interaction):
        #check the validity of the image link, is it worth it to import aiohttp for this?
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.image.value) as response:
                    if response.content_type.startswith("image"):
                        pass
                    else:
                        raise commands.BadArgument
        except:
            raise commands.BadArgument

        #we're going to need these
        kgs_guild = self.bot.get_guild(Reference.guild)
        user = kgs_guild.get_member(interaction.user.id)
        role = user.top_role
        intro_channel = kgs_guild.get_channel(
            Reference.Channels.intro_channel
        )

        if self.required:
            """We are adding a new intro so make an introduction embed"""

            description = f"**{self.timezone.value}**\n\n" + self.bio.value

            footer_name = (
                "Kurzgesagt Official"
                if role.id == Reference.Roles.kgsofficial
                else role.name
            )

            footer_icon = role.display_icon #this can return None if theres no icon
            #if role has unicode emojis, dont. not a problem in our server but just in case
            if not footer_icon.url:
                footer_icon = None

            embed = discord.Embed(description=description, color=role.color)
            embed.set_author(name=user.display_name, icon_url=user.avatar.url)
            embed.set_footer(text=footer_name, icon_url=footer_icon)
            embed.set_thumbnail(url=self.image.value)

            self.bot.intro_db.insert_one(
                {
                    "_id": interaction.user.id,
                    "tz_text": self.timezone.value,
                    "bio": self.bio.value,
                    "message_id": None,  #we will edit it with message id after reordering
                    "image": self.image.value
                }
            )

            #the command user wants some feedback
            message = f'Your intro will be added! (not really, just testing)'

        else:
            """We are editing an existing intro"""

            msg = await intro_channel.fetch_message(self.oldIntro["message_id"])
            embed = msg.embeds[0]

            #edit the embed
            embed.description = f"**{self.timezone.value}**\n\n" + self.bio.value
            embed.set_thumbnail(url=self.image.value)

            #do we need to edit the footer too?
            if embed.footer.text == role.name or role.name == "Kurzgesagt Official":
                await msg.edit(embed=embed)
                self.intro_db.update_one(
                    {"_id": interaction.user.id},
                    {"$set": {"tz_text": self.timezone.value, "bio": self.bio.value, "image": self.image.value}},
                )
            else:
                #the user got promoted or demoted
                footer_name = (
                    "Kurzgesagt Official"
                    if role.id == Reference.Roles.kgsofficial
                    else role.name
                )
                embed.color = role.color

                #we are just reusing a variable to reorder
                self.required = True


            #the command user wants some feedback
            message = f'Your intro will be edited! (not really, just testing)'

        #reorder!
        if self.required:        
            """Deletes intros that are before role_id and makes a list of tuples of the form
            (mongodb.document, discord.Embed)"""

            embeds = []
            async for message in intro_channel.history():
                if not message.embeds:
                    break

                if message.embeds[0].footer.text == role.name:
                    break

                doc = self.intro_db.find_one({"message_id": message.id})
                embeds.append((doc, message.embeds[0]))
                await message.delete()

            #now we can send the new intro message and add to mongo
            msg = await intro_channel.send(embed=embed)
            self.intro_db.update_one(
                {"_id": user.id["_id"]}, {"$set": {"message_id": msg.id}}
            )

            #add the deleted embeds back
            if embeds:
                for doc, embed in embeds:
                    msg = await intro_channel.send(embed=embed)
                    self.intro_db.update_one(
                        {"_id": doc["_id"]}, {"$set": {"message_id": msg.id}}
                    )


        #lets add server emojis, because modals dont support them
        serverEmojis = [f":{emoji.name}:" for emoji in kgs_guild.emojis]
        serverEmojiIds = [emoji.id for emoji in kgs_guild.emojis]

        embed.description = re.sub(r"(?<!<):[A-Za-z0-9_.]+:(?![0-9]+>)", lambda x: f"<{x.group()}{serverEmojiIds[serverEmojis.index(x.group())]}>" if x.group() in serverEmojis else x.group(), embed.description)


        await interaction.channel.send(embed=embed)

        #give the command user some feedback
        await interaction.response.send_message(message, ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        if isinstance(error, commands.BadArgument):
            #in the future actually do this properly
            #save the users inputs, this doc doesn't need more data
            '''currentState = {
                    "tz_text": self.timezone.value,
                    "bio": self.bio.value,
                    "image": "Incorrect image link"
                }'''
            #discordpy is not happy with sending a modal like this, look into it in the future?
            #await interaction.response.send_modal(introModal(oldIntro=currentState, bot = self.bot))
            #im just closing the modal without saving right now
            await interaction.response.send_message("Incorrect image link, sorry", ephemeral=True)
        else:
            raise error



    @app_commands.command()
    @app_commands.guilds(Reference.guild)
    @app_commands.checks.cooldown(1, 10)
    @checks.bot_commands_only()
    async def big_emote(self, interaction: discord.Interaction, emoji: str):
        """Get image for server emote

        Parameters
        ----------
        emoji: str
            Discord Emoji (only use in #bot-commands)
        """
        """
        if len(args) > 1:
            ctx.send("Please only send one emoji at a time")
        """
        print(len(demoji.findall_list(emoji)))
        if len(demoji.findall_list(emoji)) == 1:
            code = str(emoji.encode('unicode-escape')).replace('U000','-').replace('\\','').replace('\'','').replace('u','-')[2:]
            print(code)
            name = demoji.replace_with_desc(emoji).replace(' ','-').replace(":","").replace("_","-")
            await interaction.response.send_message("https://em-content.zobj.net/thumbs/160/twitter/322/" + name\
                           + "_" + code + ".png")
        elif len(demoji.findall_list(emoji)) > 1:
            await interaction.response.send_message("please only send one emoji")
        else:
            if re.match(r"<a:\w+:(\d{17,19})>", str(emoji)):
                emoji = str(re.findall(r"<a:\w+:(\d{17,19})>", str(emoji))[0]) + ".gif"
                await interaction.response.send_message("https://cdn.discordapp.com/emojis/" + str(emoji))
            elif re.match(r"<:\w+:(\d{17,19})>", str(emoji)):
                print("png")
                emoji = str(re.findall(r"<:\w+:(\d{17,19})>", str(emoji))[0]) + ".png"
                await interaction.response.send_message("https://cdn.discordapp.com/emojis/" + str(emoji))
            else:
                await interaction.response.send_message("Could not process this emoji")


async def setup(bot):
    await bot.add_cog(Misc(bot))
