import asyncio
import json
import logging
import re
import typing

import demoji
import discord
import pymongo
from discord import app_commands
from discord.ext import commands

from app.utils import checks
from app.utils.config import Reference


class Misc(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger("Misc")
        self.bot = bot
        self.intro_db = self.bot.db.StaffIntros
        self.kgs_guild: typing.Optional[discord.Guild]= None
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

        self.kgs_guild: discord.Guild= self.bot.get_guild(Reference.guild)
        assert self.kgs_guild != None

        subreddit_role = discord.utils.get(self.kgs_guild.roles, id=Reference.Roles.subreddit_mod)
        if not after.top_role >= subreddit_role:
            return

        intro = self.intro_db.find_one({"_id": before.id})
        intro_channel = self.kgs_guild.get_channel(
            Reference.Channels.intro_channel
        )
        assert intro_channel != None

        msg = await intro_channel.fetch_message(intro["message_id"])
        embed = msg.embeds[0]
        embed.set_author(name=after.display_name, icon_url=after.avatar.url)
        await msg.edit(embed=embed)

    @commands.Cog.listener()
    async def on_user_update(self, before, after):

        self.kgs_guild = self.bot.get_guild(Reference.guild)
        assert self.kgs_guild != None

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
    async def intro(self, interaction: discord.Interaction):
        """
        Staff intro command
        Create or edit an intro
        """        
        oldIntro = self.intro_db.find_one({"_id": interaction.user.id})
        await interaction.response.send_modal(self.introModal(oldIntro=oldIntro, bot = self.bot))


    class introModal(discord.ui.Modal):
        """
        The modal UI for intro commands.
        """

        def get_footer(self, role):
            footer_name = (
                "Kurzgesagt Official"
                if role.id == Reference.Roles.kgsofficial
                else role.name
            )
            footer_icon = role.icon #this can return None if there's no icon
            return footer_name, footer_icon


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
            else:
                timezone_ph = "The internet - UTC | GMT+0:00"
                bio_ph = "Hello! I'm Birdbot and I help run this server."
                image_ph = "https://cdn.discordapp.com/avatars/471705718957801483/cfcf7fbcdc9579d7f0606b014aa1ede8.png"
            
            self.timezone = discord.ui.TextInput(label='Enter your timezone.', style=discord.TextStyle.short, required=True, placeholder=timezone_ph, default = timezone_default, max_length=90)

            self.bio = discord.ui.TextInput(label='Enter your bio.', style=discord.TextStyle.paragraph, required=True, placeholder=bio_ph, default=bio_default)

            self.image = discord.ui.TextInput(label='Enter the image link for your personal bird.', style=discord.TextStyle.short, required=True, placeholder=image_ph, default=image_default)

            self.add_item(self.timezone)
            self.add_item(self.bio)
            self.add_item(self.image)

        async def on_submit(self, interaction: discord.Interaction):
            """Most of the intro command logic is here"""
            #we're going to need these
            kgs_guild = self.bot.get_guild(Reference.guild)
            user = kgs_guild.get_member(interaction.user.id)
            role = user.top_role
            intro_channel = kgs_guild.get_channel(
                Reference.Channels.intro_channel
            )
            reorder = False #will set this later
            oldIntroMessage = None #if we're adding a new intro this will remain None

            #lets add server emojis, because modals dont support them
            serverEmojis = [f":{emoji.name}:" for emoji in kgs_guild.emojis]
            serverEmojiIds = [emoji.id for emoji in kgs_guild.emojis]

            bio = re.sub(r"(?<!<):[A-Za-z0-9_.]+:(?![0-9]+>)", lambda x: f"<{x.group()}{serverEmojiIds[serverEmojis.index(x.group())]}>" if x.group() in serverEmojis else x.group(), self.bio.value)
            timezone = re.sub(r"(?<!<):[A-Za-z0-9_.]+:(?![0-9]+>)", lambda x: f"<{x.group()}{serverEmojiIds[serverEmojis.index(x.group())]}>" if x.group() in serverEmojis else x.group(), self.timezone.value)


            #update mongo
            if self.oldIntro:
                self.intro_db.update_one({"_id": user.id}, {"$set":
                {
                    "tz_text": timezone,
                    "bio": bio,
                    #"message_id": None,  #we will edit it with message id if needed, keep it for now
                    "image": self.image.value
                }}
                )
            else:
                self.intro_db.insert_one(
                    {
                        "_id": user.id,
                        "tz_text": timezone,
                        "bio": bio,
                        "message_id": None,  #we will edit it with message id after reordering
                        "image": self.image.value
                    }
                )


            #check the validity of the image link, write a better regex?
            if not re.match(r"^https*://.*\..*", self.image.value):
                await interaction.response.send_message("Incorrect image link, try again", ephemeral=True)
                return


            #if the message was deleted for some reason
            if self.oldIntro["message_id"]:
                try:
                    oldIntroMessage = await intro_channel.fetch_message(self.oldIntro["message_id"])
                except discord.NotFound:
                    self.intro_db.update_one(
                        {"_id": user.id}, {"$set": {"message_id": None}}
                    )
                    await interaction.response.send_message("The message was deleted, try again", ephemeral=True)
                    return


            if oldIntroMessage:
                """We are editing an existing intro"""
                embed = oldIntroMessage.embeds[0]

                #edit the embed
                embed.description = f"**{timezone}**\n\n" + bio
                embed.set_thumbnail(url=self.image.value)

                #do we need to edit the footer too?
                if (embed.footer.text == role.name) or (embed.footer.text == "Kurzgesagt Official" and role.id == Reference.Roles.kgsofficial):
                    await oldIntroMessage.edit(embed=embed)
                #the user got promoted or demoted
                else:
                    footer_name, footer_icon = self.get_footer(role)

                    embed.set_footer(text=footer_name, icon_url=footer_icon)
                    embed.color = role.color

                    #we want to reorder too
                    reorder = True

                #the command user wants some feedback
                message_fb = f'Your intro will be edited!'

            else:
                """We are adding a new intro so make an introduction embed"""
                description = f"**{timezone}**\n\n" + bio

                footer_name, footer_icon = self.get_footer(role)

                embed = discord.Embed(description=description, color=role.color)
                embed.set_author(name=user.display_name, icon_url=user.avatar.url)
                embed.set_footer(text=footer_name, icon_url=footer_icon)
                embed.set_thumbnail(url=self.image.value)

                reorder = True

                #the command user wants some feedback
                message_fb = f'Your intro will be added!'


            #reorder!
            if reorder:        
                """Deletes intros that are before role_id and makes a list of tuples of the form
                (mongodb.document, discord.Embed), then adds the intros back"""

                embeds = []
                async for message in intro_channel.history():
                    if not message.embeds:
                        break

                    if message.embeds[0].footer.text == role.name:
                        break

                    doc = self.intro_db.find_one({"message_id": message.id})
                    if doc:
                        embeds.append((doc, message.embeds[0]))
                        await message.delete()

                #now we can send the new intro message and add to mongo
                msg = await intro_channel.send(embed=embed)
                self.intro_db.update_one(
                    {"_id": user.id}, {"$set": {"message_id": msg.id}}
                )

                #add the deleted embeds back
                if embeds:
                    for doc, embed in embeds:
                        msg = await intro_channel.send(embed=embed)
                        self.intro_db.update_one(
                            {"_id": doc["_id"]}, {"$set": {"message_id": msg.id}}
                        )


            #give the command user some feedback
            await interaction.response.send_message(message_fb, ephemeral=True)



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
