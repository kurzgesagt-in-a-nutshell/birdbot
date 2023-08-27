import logging
import asyncio
import json
import re

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
        subreddit_role = discord.utils.get(
            self.kgs_guild.roles, id=Reference.Roles.subreddit_mod
        )
        if not after.top_role >= subreddit_role:
            return

        intro = self.intro_db.find_one({"_id": before.id})
        intro_channel = self.kgs_guild.get_channel(Reference.Channels.intro_channel)
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
        subreddit_role = discord.utils.get(
            self.kgs_guild.roles, id=Reference.Roles.subreddit_mod
        )
        if not member.top_role >= subreddit_role:
            return

        intro = self.intro_db.find_one({"_id": before.id})
        intro_channel = self.kgs_guild.get_channel(Reference.Channels.intro_channel)
        msg = await intro_channel.fetch_message(intro["message_id"])
        embed = msg.embeds[0]
        embed.set_author(name=member.display_name, icon_url=after.avatar.url)
        await msg.edit(embed=embed)

    def parse_info(self, user_id, tz_text, bio, bird_icon):
        """Get all the neccesary info and return an introduction embed"""
        user = self.kgs_guild.get_member(user_id)
        description = f"**{tz_text}**\n\n" + bio
        footer_name = (
            "Kurzgesagt Official"
            if user.top_role.id == Reference.Roles.kgsofficial
            else user.top_role.name
        )
        footer_icon = self.config["roleicons"][f"{user.top_role.id}"]
        embed = discord.Embed(description=description, color=user.top_role.color)
        embed.set_author(name=user.display_name, icon_url=user.avatar.url)
        embed.set_footer(text=footer_name, icon_url=footer_icon)
        embed.set_thumbnail(url=bird_icon)
        return embed

    async def reorder_intros(self, role, intro_channel) -> tuple:
        """Deletes intros that are before role_id and returns list of tuples of the form
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

        return embeds

    @checks.role_and_above(
        Reference.Roles.subreddit_mod
    )  # subreddit mods and above | exludes trainees
    @commands.group(hidden=True)
    async def intro(self, ctx):
        """
        Staff intro commands
        Usage: intro add/edit
        """

    @intro.command()
    async def add(self, ctx):

        self.kgs_guild = self.bot.get_guild(Reference.guild)

        intro = self.intro_db.find_one({"_id": ctx.author.id})
        if intro:
            await ctx.send(
                "It looks like you already have an intro. Use '!intro edit' to make changes to it"
            )
            return

        def check(m):
            return m.channel == ctx.channel and m.author == ctx.author

        try:
            await ctx.send(
                "Enter your timezone. This info need not neccesarily be accurate and can be memed."
            )
            tz_text = await self.bot.wait_for("message", check=check, timeout=180)
            await ctx.send("Okay, Enter your bio")
            bio = await self.bot.wait_for("message", check=check, timeout=240)
            await ctx.send(
                "Neat bio. Now give me the image link for your personal bird. The image should be fully transparent"
            )
            img = await self.bot.wait_for("message", check=check, timeout=240)
            if not img.content.startswith("http"):  # dont wanna use regex
                await ctx.send(
                    "That does not appear to be a valid link. Please run the command again"
                )
                return
        except asyncio.TimeoutError:
            await ctx.send(
                "You took too long to respond :(\nPlease run the command again"
            )
            return
        else:
            embed = self.parse_info(
                ctx.author.id, tz_text.content, bio.content, img.content
            )
            intro_channel = self.kgs_guild.get_channel(Reference.Channels.intro_channel)

            embeds_to_add = await self.reorder_intros(
                ctx.author.top_role, intro_channel
            )
            msg = await intro_channel.send(embed=embed)
            self.intro_db.insert_one(
                {
                    "_id": ctx.author.id,
                    "tz_text": tz_text.content,
                    "bio": bio.content,
                    "message_id": msg.id,
                }
            )

            if embeds_to_add:
                for doc, embed in embeds_to_add:
                    msg = await intro_channel.send(embed=embed)
                    self.intro_db.update_one(
                        {"_id": doc["_id"]}, {"$set": {"message_id": msg.id}}
                    )

            await ctx.send("Success.")

    @intro.command()
    async def edit(self, ctx):

        self.kgs_guild = self.bot.get_guild(Reference.guild)
        intro = self.intro_db.find_one({"_id": ctx.author.id})
        if not intro:
            await ctx.send(
                "It looks like you dont have an intro. Use '!intro add' to add one"
            )
            return

        def check(m):
            return m.channel == ctx.channel and m.author == ctx.author

        try:
            await ctx.send(
                "Enter your timezone. This info need not neccesarily be accurate and can be memed.\nType `skip` if you want to leave this unchanged"
            )
            tz_text = await self.bot.wait_for("message", check=check, timeout=180)
            if tz_text.content.lower() == "skip":
                str_tz_text = intro["tz_text"]
            else:
                str_tz_text = tz_text.content

            await ctx.send(
                "Okay, Enter your bio. Type 'skip' if you want to leave this unchanged"
            )
            bio = await self.bot.wait_for("message", check=check, timeout=240)
            if bio.content.lower() == "skip":
                str_bio = intro["bio"]
            else:
                str_bio = bio.content

        except asyncio.TimeoutError:
            await ctx.send(
                "You took too long to respond :( Please run the command again"
            )
            return
        else:
            intro_channel = self.kgs_guild.get_channel(Reference.Channels.intro_channel)
            msg = await intro_channel.fetch_message(intro["message_id"])
            embed = msg.embeds[0]
            embed.description = f"**{str_tz_text}**\n\n" + str_bio
            await msg.edit(embed=embed)

            self.intro_db.update_one(
                {"_id": ctx.author.id},
                {"$set": {"tz_text": str_tz_text, "bio": str_bio}},
            )
            await ctx.send("Success.")

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
            code = (
                str(emoji.encode("unicode-escape"))
                .replace("U000", "-")
                .replace("\\", "")
                .replace("'", "")
                .replace("u", "-")[2:]
            )
            print(code)
            name = (
                demoji.replace_with_desc(emoji)
                .replace(" ", "-")
                .replace(":", "")
                .replace("_", "-")
            )
            await interaction.response.send_message(
                "https://em-content.zobj.net/thumbs/160/twitter/322/"
                + name
                + "_"
                + code
                + ".png"
            )
        elif len(demoji.findall_list(emoji)) > 1:
            await interaction.response.send_message("please only send one emoji")
        else:
            if re.match(r"<a:\w+:(\d{17,19})>", str(emoji)):
                emoji = str(re.findall(r"<a:\w+:(\d{17,19})>", str(emoji))[0]) + ".gif"
                await interaction.response.send_message(
                    "https://cdn.discordapp.com/emojis/" + str(emoji)
                )
            elif re.match(r"<:\w+:(\d{17,19})>", str(emoji)):
                print("png")
                emoji = str(re.findall(r"<:\w+:(\d{17,19})>", str(emoji))[0]) + ".png"
                await interaction.response.send_message(
                    "https://cdn.discordapp.com/emojis/" + str(emoji)
                )
            else:
                await interaction.response.send_message("Could not process this emoji")


async def setup(bot):
    await bot.add_cog(Misc(bot))
