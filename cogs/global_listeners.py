import io
import asyncio
import json
import aiohttp
import logging
import random
import re

from traceback import TracebackException

import discord
from discord.ext import commands
from discord.ext.commands import errors

from utils.helper import (
    NoAuthorityError,
    DevBotOnly,
    WrongChannel,
    patreon_only,
    create_user_infraction,
)


class GuildChores(commands.Cog):
    """Chores that need to performed during guild events"""

    def __init__(self, bot):
        self.logger = logging.getLogger("Guild Chores")
        self.bot = bot

        with open("config.json", "r") as config_file:
            self.config_json = json.loads(config_file.read())

        self.mod_role = self.config_json["roles"]["mod_role"]
        self.admin_role = self.config_json["roles"]["admin_role"]
        self.patreon_roles = [
            self.config_json["roles"]["patreon_blue_role"],
            self.config_json["roles"]["patreon_green_role"],
            self.config_json["roles"]["patreon_orange_role"],
        ]
        self.pfp_list = [
            "https://cdn.discordapp.com/emojis/909047588160942140.png?size=256",
            "https://cdn.discordapp.com/emojis/909047567030059038.png?size=256",
            "https://cdn.discordapp.com/emojis/909046980599250964.png?size=256",
            "https://cdn.discordapp.com/emojis/909047000253734922.png?size=256",
        ]
        self.greeting_webhook_url = "https://discord.com/api/webhooks/909052135864410172/5Fky0bSJMC3vh3Pz69nYc2PfEV3W2IAwAsSFinBFuUXXzDc08X5dv085XlLDGz3MmQvt"

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info("Loaded Guild Chores")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Remind mods to use correct prefix"""
        if not message.author.bot:
            guild = discord.utils.get(self.bot.guilds, id=414027124836532234)
            mod_role = discord.utils.get(guild.roles, id=self.mod_role)
            admin_role = discord.utils.get(guild.roles, id=self.admin_role)

            if not (
                (mod_role in message.author.roles)
                or (admin_role in message.author.roles)
            ):
                return
            if re.match("^-(kick|ban|mute|warn)", message.content):
                await message.channel.send(f"ahem.. {message.author.mention}")

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """Grant roles upon passing membership screening"""

        if before.pending and (not after.pending):
            guild = discord.utils.get(self.bot.guilds, id=414027124836532234)
            await after.add_roles(
                guild.get_role(542343829785804811),  # Verified
                guild.get_role(901136119863844864),  # English
                reason="Membership screening passed",
            )

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Listen for new patrons and provide
        them the option to unenroll from autojoining
        Listen for new members and fire webhook for greeting"""

        diff_roles = [role.id for role in member.roles]
        if any(x in diff_roles for x in self.patreon_roles):

            guild = discord.utils.get(self.bot.guilds, id=414027124836532234)
            await member.add_roles(
                guild.get_role(542343829785804811),  # Verified
                guild.get_role(901136119863844864),  # English
            )

            try:
                embed = discord.Embed(
                    title="Hey there patron! Annoyed about auto-joining the server?",
                    description="Unfortunately Patreon doesn't natively support a way to disable this- "
                    "but you have the choice of getting volutarily banned from the server "
                    "therby preventing your account from rejoining. To do so simply type ```!unenroll```"
                    "If you change your mind in the future just fill out [this form!](https://forms.gle/m4KPj2Szk1FKGE6F8)",
                    color=0xFFFFFF,
                )
                embed.set_thumbnail(
                    url="https://cdn.discordapp.com/emojis/824253681443536896.png?size=256"
                )

                await member.send(embed=embed)
            except discord.Forbidden:
                return
        else:
            async with aiohttp.ClientSession() as session:
                hook = discord.Webhook.from_url(
                    self.greeting_webhook_url,
                    adapter=discord.AsyncWebhookAdapter(session),
                )
                await hook.send(
                    f"Welcome hatchling {member.mention}!\n"
                    "Make sure to read the <#414268041787080708> and say hello to our <@&584461501109108738>s",
                    avatar_url=random.choice(self.pfp_list),
                    allowed_mentions=discord.AllowedMentions(users=True, roles=True),
                )

    @patreon_only()
    @commands.command()
    async def unenroll(self, ctx):
        self.logger.info("Command called")
        embed = discord.Embed(
            title="We're sorry to see you go",
            description="Are you sure you want to get banned from the server?"
            " If you change your mind in the future you can simply fill out [this form.](https://forms.gle/m4KPj2Szk1FKGE6F8)",
            color=0xFFCB00,
        )
        embed.set_thumbnail(
            url="https://cdn.discordapp.com/emojis/736621027093774467.png?size=96"
        )

        def check(reaction, user):
            return user == ctx.author

        fallback_embed = discord.Embed(
            title="Action Cancelled",
            description="Phew, That was close.",
            color=0x00FFA9,
        )

        try:
            confirm_msg = await ctx.author.send(embed=embed)
            await confirm_msg.add_reaction("<:kgsYes:580164400691019826>")
            await confirm_msg.add_reaction(":kgsNo:610542174127259688>")
            reaction, user = await self.bot.wait_for(
                "reaction_add", timeout=120, check=check
            )

            if reaction.emoji.id == 580164400691019826:

                member = discord.utils.get(
                    self.bot.guilds, id=414027124836532234
                ).get_member(ctx.author.id)

                infraction_db = BirdBot.db.Infraction

                inf = infraction_db.find_one({"user_id": ctx.author.id})
                if inf is None:
                    create_user_infraction(ctx.author)

                    inf = infraction_db.find_one({"user_id": ctx.author.id})
                infraction_db.update_one(
                    {"user_id": ctx.author.id}, {"$set": {"banned_patron": True}}
                )

                await ctx.author.send("Success! You've been banned from the server.")
                await member.ban(reason="Patron Voluntary Removal")
                return
            if reaction.emoji.id == 610542174127259688:
                await confirm_msg.edit(embed=fallback_embed)
                return

        except discord.Forbidden:
            await ctx.send(
                "I can't seem to DM you. please check your privacy settings and try again"
            )

        except asyncio.TimeoutError:
            await confirm_msg.edit(embed=fallback_embed)


class Errors(commands.Cog):
    """Catches all exceptions coming in through commands"""

    def __init__(self, bot):
        with open("config.json", "r") as config_file:
            self.config_json = json.loads(config_file.read())
        self.dev_logging_channel = self.config_json["logging"]["dev_logging_channel"]

        self.logger = logging.getLogger("Listeners")
        self.bot = bot

    async def react_send_delete(
        self,
        ctx: commands.Context,
        reaction: str = None,
        message: str = None,
        delay: int = 6,
    ):
        """React to the command, send a message and delete later"""
        if reaction is not None:
            await ctx.message.add_reaction(reaction)
        if message is not None:
            await ctx.send(message, delete_after=delay)
        await asyncio.sleep(delay)
        await ctx.message.delete()

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info("loaded Error listener")

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, err):

        traceback_txt = "".join(TracebackException.from_exception(err).format())
        channel = await self.bot.fetch_channel(self.dev_logging_channel)

        if isinstance(
            err, (errors.MissingPermissions, NoAuthorityError, errors.NotOwner)
        ):
            await self.react_send_delete(ctx, reaction="<:kgsNo:610542174127259688>")

        elif isinstance(err, DevBotOnly):
            await self.react_send_delete(
                ctx,
                message="This command can only be run on the main bot",
                reaction="<:kgsNo:610542174127259688>",
            )

        elif isinstance(err, commands.MissingRequiredArgument):
            await self.react_send_delete(
                ctx,
                message=f"You're missing the {err.param.name} argument. Please check syntax using the help command.",
                reaction="<:kgsNo:610542174127259688>",
            )

        elif isinstance(err, commands.CommandNotFound):
            pass

        elif isinstance(err, errors.CommandOnCooldown):
            await self.react_send_delete(ctx, reaction="\U000023f0", delay=4)

        elif isinstance(err, (WrongChannel, errors.BadArgument)):
            await self.react_send_delete(
                ctx,
                message=err,
                reaction="<:kgsNo:610542174127259688>",
                delay=4,
            )

        else:
            self.logger.exception(traceback_txt)
            await ctx.message.add_reaction("<:kgsStop:579824947959169024>")
            await ctx.send(
                "Uh oh, an unhandled exception occured, if this issue persists please contact FC or sloth"
            )
            description = (
                f"An [**unhandled exception**]({ctx.message.jump_url}) occured in <#{ctx.message.channel.id}> when "
                f"running the **{ctx.command.name}** command.```\n{err}```"
            )
            embed = discord.Embed(
                title="Unhandled Exception", description=description, color=0xFF0000
            )
            file = discord.File(
                io.BytesIO(traceback_txt.encode()), filename="traceback.txt"
            )
            await channel.send(embed=embed, file=file)


def setup(bot):
    bot.add_cog(Errors(bot))
    bot.add_cog(GuildChores(bot))
