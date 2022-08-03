import logging
import asyncio
import json
import discord
import pymongo

# Do not import panda for VM.
# import pandas as pd
from discord.ext import commands

from utils.helper import role_and_above

# Mongo schema to store intros
# {
# "_id": user_id,
# "message_id": message_id,
# "tz_text": timezone_text,
# "bio": bio
# }


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

        self.kgs_guild = self.bot.get_guild(414027124836532234)
        subreddit_role = discord.utils.get(self.kgs_guild.roles, id=681812574026727471)
        if not after.top_role >= subreddit_role:
            return

        intro = self.intro_db.find_one({"_id": before.id})
        intro_channel = self.kgs_guild.get_channel(
            self.config["logging"]["intro_channel"]
        )
        msg = await intro_channel.fetch_message(intro["message_id"])
        embed = msg.embeds[0]
        embed.set_author(name=after.display_name, icon_url=after.avatar_url)
        await msg.edit(embed=embed)

    @commands.Cog.listener()
    async def on_user_update(self, before, after):

        self.kgs_guild = self.bot.get_guild(414027124836532234)

        member = self.kgs_guild.get_member(before.id)
        if not member:
            return
        subreddit_role = discord.utils.get(self.kgs_guild.roles, id=681812574026727471)
        if not member.top_role >= subreddit_role:
            return

        intro = self.intro_db.find_one({"_id": before.id})
        intro_channel = self.kgs_guild.get_channel(
            self.config["logging"]["intro_channel"]
        )
        msg = await intro_channel.fetch_message(intro["message_id"])
        embed = msg.embeds[0]
        embed.set_author(name=member.display_name, icon_url=after.avatar_url)
        await msg.edit(embed=embed)

    def parse_info(self, user_id, tz_text, bio, bird_icon):
        """Get all the neccesary info and return an introduction embed"""
        user = self.kgs_guild.get_member(user_id)
        description = f"**{tz_text}**\n\n" + bio
        footer_name = (
            "Kurzgesagt Official"
            if user.top_role.id == 915629257470906369
            else user.top_role.name
        )
        footer_icon = self.config["roleicons"][f"{user.top_role.id}"]
        embed = discord.Embed(description=description, color=user.top_role.color)
        embed.set_author(name=user.display_name, icon_url=user.avatar_url)
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

    @role_and_above(681812574026727471)  # subreddit mods and above | exludes trainees
    @commands.group(hidden=True)
    async def intro(self, ctx):
        """
        Staff intro commands
        Usage: intro add/edit
        """

    @intro.command()
    async def add(self, ctx):

        self.kgs_guild = self.bot.get_guild(414027124836532234)

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
            intro_channel = self.kgs_guild.get_channel(
                self.config["logging"]["intro_channel"]
            )

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

        self.kgs_guild = self.bot.get_guild(414027124836532234)
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
            intro_channel = self.kgs_guild.get_channel(
                self.config["logging"]["intro_channel"]
            )
            msg = await intro_channel.fetch_message(intro["message_id"])
            embed = msg.embeds[0]
            embed.description = f"**{str_tz_text}**\n\n" + str_bio
            await msg.edit(embed=embed)

            self.intro_db.update_one(
                {"_id": ctx.author.id},
                {"$set": {"tz_text": str_tz_text, "bio": str_bio}},
            )
            await ctx.send("Success.")

    @commands.command()
    @commands.is_owner()
    async def mod_intros(self, ctx):
        """Only works with the intro spreadsheet. For local testing only."""
        df = pd.read_csv("intro.csv")

        self.kgs_guild = self.bot.get_guild(414027124836532234)
        intro_channel = self.kgs_guild.get_channel(
            self.config["logging"]["intro_channel"]
        )
        for _, row in df.iterrows():
            user = self.kgs_guild.get_member(int(row["ID"]))
            bird_icon = self.config["roleicons"][f"{user.top_role.id}"]
            embed = self.parse_info(
                int(row["ID"]), row["Region"], row["Bio"], row["Bird"]
            )
            msg = await intro_channel.send(embed=embed)
            try:
                self.intro_db.insert_one(
                    {
                        "_id": int(row["ID"]),
                        "tz_text": row["Region"],
                        "bio": row["Bio"],
                        "message_id": msg.id,
                    }
                )
            except pymongo.errors.DuplicateKeyError:
                pass


def setup(bot):
    bot.add_cog(Misc(bot))
