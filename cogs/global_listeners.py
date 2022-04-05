import io
import asyncio
import json
import aiohttp
import logging
import random
import re
import datetime

from traceback import TracebackException

import discord
from discord.ext import commands
from discord.ext.commands import errors

from birdbot import BirdBot

from utils.helper import (
    NoAuthorityError,
    DevBotOnly,
    WrongChannel,
    patreon_only,
    create_user_infraction,
    is_internal_command,
)

#janky fix for server memories, will make permanent once out of experimentation
async def check_server_memories(message):

    if message.channel.id == 960927545639972994:  # server memories // media only
        if any(_id in [role.id for role in message.author.roles] for _id in [414092550031278091,414029841101225985]): #mod or admin
            return
        if message.author.bot:
            return
        if len(message.attachments) == 0 and len(message.embeds) == 0:
            await message.delete()
            await message.channel.send(
                f"{message.author.mention} You can only send screenshots in this channel. ",
                delete_after=5,
            )
            return
        else:
            for e in message.embeds:
                if e.type != "image":
                    await message.delete()
                    await message.channel.send(
                        f"{message.author.mention} You can only send screenshots in this channel. ",
                        delete_after=5,
                    )
                    return


class GuildLogger(commands.Cog):
    """Log events neccesary for moderation"""

    def __init__(self, bot):
        self.logger = logging.getLogger("Guild Logs")
        self.bot = bot

        with open("config.json", "r") as config_file:
            self.config_json = json.loads(config_file.read())

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info("Loaded Guild Event Logging")

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):

        # mainbot only
        if self.bot.user.id != 471705718957801483:
            return

        if before.guild.id != 414027124836532234:  # kgs guild id
            return
        if before.author.bot:
            return

        await check_server_memories(after)
        if (
            before.channel.category.id == 414095379156434945
            or before.channel.category.id == 879399341561892905
        ):
            # mod category and logging category gets ignored
            return
        if before.content == after.content:
            return

        embed = discord.Embed(
            title="Message Edited",
            description=f"Message edited in {before.channel.mention}",
            color=0xEE7600,
            timestamp=datetime.datetime.utcnow(),
        )
        embed.set_author(
            name=before.author.display_name, icon_url=before.author.avatar_url
        )
        embed.add_field(name="Before", value=before.content, inline=False)
        embed.add_field(name="After", value=after.content, inline=False)
        search_terms = f"""
                        ```Edited in {before.channel.id}\nEdited by {before.author.id}\nMessage edited in {before.channel.id} by {before.author.id}```
                        """

        embed.add_field(name="Search terms", value=search_terms, inline=False)
        embed.set_footer(
            text="Input the search terms in your discord search bar to easily sort through specific logs"
        )

        message_logging_channel = self.bot.get_channel(
            self.config_json["logging"]["message_logging_channel"]
        )
        await message_logging_channel.send(embed=embed)


    @commands.Cog.listener()
    async def on_message_delete(self, message):

        # mainbot only
        if self.bot.user.id != 471705718957801483:
            return

        if message.guild.id != 414027124836532234:  # kgs guild id
            return
        if message.author.bot:
            return
        if message.channel.category.id == 414095379156434945:  # mod category
            return

        if is_internal_command(self.bot, message):
            return

        embed = discord.Embed(
            title="Message Deleted",
            description=f"Message deleted in {message.channel.mention}",
            color=0xC9322C,
            timestamp=datetime.datetime.utcnow(),
        )
        embed.set_author(
            name=message.author.display_name, icon_url=message.author.avatar_url
        )
        embed.add_field(name="Content", value=message.content)
        search_terms = f"```Deleted in {message.channel.id}"

        latest_logged_delete = await message.guild.audit_logs(
            limit=1, action=discord.AuditLogAction.message_delete
        ).flatten()
        latest_logged_delete = latest_logged_delete[0]

        self_deleted = False
        if message.author == latest_logged_delete.target:
            embed.description += f"\nDeleted by {latest_logged_delete.user.mention} {latest_logged_delete.user.name}"
            search_terms += f"\nDeleted by {latest_logged_delete.user.id}"
        else:
            self_deleted = True
            search_terms += f"\nDeleted by {message.author.id}"
            embed.description += (
                f"\nDeleted by {message.author.mention} {message.author.name}"
            )

        search_terms += f"\nSent by {message.author.id}"
        search_terms += f"\nMessage from {message.author.id} deleted by {message.author.id if self_deleted else latest_logged_delete.user.id} in {message.channel.id}```"

        embed.add_field(name="Search terms", value=search_terms, inline=False)
        embed.set_footer(
            text="Input the search terms in your discord search bar to easily sort through specific logs"
        )

        message_logging_channel = self.bot.get_channel(
            self.config_json["logging"]["message_logging_channel"]
        )
        await message_logging_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member):

        # mainbot only

        if self.bot.user.id != 471705718957801483:
            return

        # remind mods to screenshot milestone
        if len(member.guild.members) == 69410:

            mod_channel = self.bot.get_channel(414095428573986816)
            await mod_channel.send(
                "<@&414092550031278091> we are ten members away for 69420!! Someone get the screenshot"
            )

        embed = discord.Embed(
            title="Member joined",
            description=f"{member.name}#{member.discriminator} ({member.id}) {member.mention}",
            color=0x45E65A,
            timestamp=datetime.datetime.utcnow(),
        )
        embed.set_author(name=member.name, icon_url=member.avatar_url)

        embed.add_field(
            name="Account Created",
            value=f"<t:{round(member.created_at.timestamp())}:R>",
            inline=True,
        )

        embed.add_field(
            name="Search terms", value=f"```{member.id} joined```", inline=False
        )
        embed.set_footer(
            text="Input the search terms in your discord search bar to easily sort through specific logs"
        )

        member_logging_channel = self.bot.get_channel(
            self.config_json["logging"]["member_logging_channel"]
        )
        await member_logging_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):

        # mainbot only
        if self.bot.user.id != 471705718957801483:
            return

        embed = discord.Embed(
            title="Member Left",
            description=f"{member.name}#{member.discriminator} ({member.id})",
            color=0xFF0004,
            timestamp=datetime.datetime.utcnow(),
        )
        embed.set_author(name=member.name, icon_url=member.avatar_url)
        acc_age = datetime.datetime.utcnow() - member.created_at

        embed.add_field(
            name="Account Created",
            value=f"<t:{round(member.created_at.timestamp())}:R>",
            inline=True,
        )
        embed.add_field(
            name="Joined Server",
            value=f"<t:{round(member.joined_at.timestamp())}:R>",
            inline=True,
        )
        embed.add_field(
            name="Roles",
            value=f"{' '.join([role.mention for role in member.roles])}",
            inline=False,
        )

        embed.add_field(
            name="Search terms", value=f"```{member.id} left```", inline=False
        )
        embed.set_footer(
            text="Input the search terms in your discord search bar to easily sort through specific logs"
        )

        member_logging_channel = self.bot.get_channel(
            self.config_json["logging"]["member_logging_channel"]
        )
        await member_logging_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):

        # mainbot only
        if self.bot.user.id != 471705718957801483:
            return

        if before.nick == after.nick:
            return

        embed = discord.Embed(
            title="Nickname changed",
            description=f"{before.name}#{before.discriminator} ({before.id})",
            color=0xFF6633,
            timestamp=datetime.datetime.utcnow(),
        )
        embed.set_author(name=before.name, icon_url=before.avatar_url)
        embed.add_field(name="Previous Nickname", value=f"{before.nick}", inline=True)
        embed.add_field(name="Current Nickname", value=f"{after.nick}", inline=True)

        embed.add_field(
            name="Search terms",
            value=f"```{before.id} changed nickname```",
            inline=False,
        )
        embed.set_footer(
            text="Input the search terms in your discord search bar to easily sort through specific logs"
        )

        member_logging_channel = self.bot.get_channel(
            self.config_json["logging"]["member_logging_channel"]
        )
        await member_logging_channel.send(embed=embed)


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
        """Remind mods to use correct prefix, alert mod pings etc"""

        await check_server_memories(message)
        if any(
            x in message.raw_role_mentions
            for x in [414092550031278091, 905510680763969536]
        ):
            if message.channel.category.id == 414095379156434945:  # mod category
                return

            role_names = [
                discord.utils.get(message.guild.roles, id=role).name
                for role in message.raw_role_mentions
            ]
            mod_channel = self.bot.get_channel(414095428573986816)
            # mod_channel = self.bot.get_channel(414179142020366336)

            embed = discord.Embed(
                title="Mod ping alert!",
                description=f"{' and '.join(role_names)} got pinged in {message.channel.mention} - [view message]({message.jump_url})",
                color=0x00FF00,
            )
            embed.set_author(
                name=message.author.display_name, icon_url=message.author.avatar_url
            )
            embed.set_footer(
                text="Last 50 messages in the channel are attached for reference"
            )

            to_file = ""
            async for msg in message.channel.history(limit=50):
                to_file += f"{msg.author.display_name}: {msg.content}\n"

            await mod_channel.send(
                embed=embed,
                file=discord.File(io.BytesIO(to_file.encode()), filename="history.txt"),
            )

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

        # mainbot only
        if self.bot.user.id != 471705718957801483:
            return

        # temp fix to remove clonex bots
        if "clonex" in str(member.name).lower():
            guild = discord.utils.get(self.bot.guilds, id=414027124836532234)
            await guild.kick(member)
            return

        diff_roles = [role.id for role in member.roles]
        if any(x in diff_roles for x in self.patreon_roles):

            guild = discord.utils.get(self.bot.guilds, id=414027124836532234)
            await member.add_roles(
                guild.get_role(542343829785804811),  # Verified
                guild.get_role(901136119863844864),  # English
                reason="Patron auto join",
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
            if BirdBot.currently_raided:
                return
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
        embed = discord.Embed(
            title="We're sorry to see you go",
            description="Are you sure you want to get banned from the server?"
            "If you change your mind in the future you can simply fill out [this form.](https://forms.gle/m4KPj2Szk1FKGE6F8)",
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
            await confirm_msg.add_reaction("<:kgsYes:955703069516128307>")
            await confirm_msg.add_reaction("<:kgsNo:955703108565098496>")
            reaction, user = await self.bot.wait_for(
                "reaction_add", timeout=120, check=check
            )

            if reaction.emoji.id == 955703069516128307:

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
            if reaction.emoji.id == 955703108565098496:
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
        await ctx.message.delete(delay=delay)

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info("loaded Error listener")

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, err):

        traceback_txt = "".join(TracebackException.from_exception(err).format())
        channel = await self.bot.fetch_channel(self.dev_logging_channel)

        if isinstance(
            err,
            (
                errors.MissingPermissions,
                NoAuthorityError,
                errors.NotOwner,
                errors.CheckAnyFailure,
            ),
        ):
            await self.react_send_delete(ctx, reaction="<:kgsNo:955703108565098496>")

        elif isinstance(err, DevBotOnly):
            await self.react_send_delete(
                ctx,
                message="This command can only be run on the main bot",
                reaction="<:kgsNo:955703108565098496>",
            )

        elif isinstance(err, commands.MissingRequiredArgument):
            await self.react_send_delete(
                ctx,
                message=f"You're missing the {err.param.name} argument. Please check syntax using the help command.",
                reaction="<:kgsNo:955703108565098496>",
            )

        elif isinstance(err, commands.CommandNotFound):
            pass

        elif isinstance(err, errors.CommandOnCooldown):
            await self.react_send_delete(ctx, reaction="\U000023f0", delay=4)

        elif isinstance(err, (WrongChannel, errors.BadArgument)):
            await self.react_send_delete(
                ctx,
                message=err,
                reaction="<:kgsNo:955703108565098496>",
                delay=4,
            )

        else:
            self.logger.exception(traceback_txt)
            await ctx.message.add_reaction("<:kgsStop:579824947959169024>")
            await ctx.send(
                "Uh oh, an unhandled exception occured, if this issue persists please contact any of bot devs (Sloth, FC, Austin, Orav)."
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
    bot.add_cog(GuildLogger(bot))
