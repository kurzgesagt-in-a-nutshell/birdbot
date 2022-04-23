from ast import alias
import json
import io
import re
import typing
import datetime
import asyncio
import logging

from discord import http
from discord.channel import DMChannel


from utils import custom_converters
from utils import helper
from utils.helper import (
    append_infraction,
    devs_only,
    get_single_infraction_type,
    mod_and_above,
    calc_time,
    get_active_staff,
    blacklist_member,
    whitelist_member,
)

import discord
from discord.ext import commands, tasks


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger("Moderation")
        self.bot = bot

        config_file = open("config.json", "r")
        self.config_json = json.loads(config_file.read())
        config_file.close()

        self.logging_channel = self.config_json["logging"]["logging_channel"]
        self.message_logging_channel = self.config_json["logging"][
            "message_logging_channel"
        ]
        self.mod_role = self.config_json["roles"]["mod_role"]
        self.admin_role = self.config_json["roles"]["admin_role"]

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info("loaded Moderation")

    @commands.command()
    async def report(
        self,
        ctx,
        user_id: str = None,
        message_link: str = None,
        *,
        extras: str = None,
    ):
        """Report an issue to the authorites. Use this command in the bots DMs\n Usage: report\nreport user_ID message_link description_of_issue"""

        if message_link and not message_link.startswith("http"):
            if extras:
                extras = f"{message_link} {extras}"
            else:
                extras = f"{message_link}"

        mod_embed = discord.Embed(title="New Report", color=0x00FF00)
        mod_embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)

        def check(msg):
            return msg.author == ctx.author and isinstance(
                msg.channel, discord.DMChannel
            )

        if user_id is None:
            try:
                msg = await ctx.author.send(
                    embed=discord.Embed(
                        title="Thanks for reaching out!",
                        description="Briefly describe your issue",
                        color=0xFF69B4,
                    )
                )
                report_desc = await self.bot.wait_for(
                    "message", timeout=120, check=check
                )
                extras = report_desc.content

                await msg.edit(
                    embed=discord.Embed(
                        title="Report description noted!",
                        description='If you have a [User ID](https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID-) for the person you\'re reporting against please enter them, else type "no"',
                    )
                )
                user_id_desc = await self.bot.wait_for(
                    "message", timeout=120, check=check
                )
                if not "no" in user_id_desc.content.lower():
                    report_user = self.bot.get_user(int(user_id_desc.content))
                    if report_user is not None:
                        user_id = f"({user_id_desc.content}) {report_user.name}"

                await msg.edit(
                    embed=discord.Embed(
                        title="Got it!",
                        description='Finally do you happen to have a message link? type "no" if not',
                    )
                )

                link_desc = await self.bot.wait_for("message", timeout=120, check=check)
                if not "no" in link_desc.content.lower():
                    message_link = link_desc.content

                await msg.edit(
                    embed=discord.Embed(
                        title="Report Successful!",
                        description="Your report has been sent to the proper authorities.",
                        color=0x00FF00,
                    )
                )

            except discord.Forbidden:
                await ctx.send(
                    "I can't seem to DM you, please check your privacy settings and try again"
                )
                return
            except asyncio.TimeoutError:
                await msg.edit(
                    embed=discord.Embed(
                        title="Report timed out",
                        description="Oops please try again",
                        color=0xFF0000,
                    )
                )
                return

        if isinstance(ctx.channel, discord.DMChannel):
            channel = "User DM"
        else:
            channel = ctx.channel.mention

        mod_embed.description = f"**Report description: ** {extras}\n**User: ** {user_id}\n**Message Link: ** [click to jump]({message_link})\n**Channel: ** {channel}"

        mod_channel = self.bot.get_channel(414095428573986816)
        await mod_channel.send(
            content=get_active_staff(self.bot),
            embed=mod_embed,
            allowed_mentions=discord.AllowedMentions(roles=True, users=True),
        )

    @mod_and_above()
    @commands.command(aliases=["purge", "prune", "clear"])
    async def clean(
        self,
        ctx: commands.Context,
        member: commands.Greedy[discord.Member] = None,
        msg_count: int = None,
        channel: discord.TextChannel = None,
    ):
        """Clean messages. \nUsage: clean <@member(s)/ id(s)> number_of_messages <#channel>"""
        messsage_count = msg_count  # used to display number of messages deleted
        if msg_count is None:
            return await ctx.send(
                f"**Usage:** `clean <@member(s)/ id(s)> number_of_messages <#channel>`"
            )

        if msg_count > 200:
            return await ctx.send(f"Provided number is too big. (Max limit 100)")

        if msg_count <= 0:
            return await ctx.channel.purge(limit=1)

        if channel is None:
            channel = ctx.channel

        # check if message sent is by a user who is in command argument
        def check(m):
            if m.author in member:
                nonlocal messsage_count
                messsage_count -= 1
                if messsage_count >= 0:
                    return True
            return False

        if not member:
            deleted_messages = await channel.purge(limit=msg_count + 1)
        else:
            deleted_messages = await channel.purge(limit=150, check=check)

        await ctx.send(
            f"Deleted {len(deleted_messages) - 1} message(s)", delete_after=3.0
        )

        message_logging_channel = discord.utils.get(
            ctx.guild.channels, id=self.message_logging_channel
        )

        if msg_count == 1:

            embed = helper.create_embed(
                author=ctx.author,
                action="1 message deleted",
                users=None,
                extra=f"""Message Content: {deleted_messages[-1].content} 
                                              \nSender: {deleted_messages[-1].author.mention} 
                                              \nTime: {deleted_messages[-1].created_at.replace(microsecond=0)} 
                                              \nID: {deleted_messages[-1].id} 
                                              \nChannel: {channel.mention}""",
                color=discord.Color.green(),
            )

            await message_logging_channel.send(embed=embed)

        else:
            # formatting string to be sent as file for logging
            log_str = (
                "Author (ID)".ljust(70)
                + " | "
                + "Message Creation Time (UTC)".ljust(30)
                + " | "
                + "Content"
                + "\n\n"
            )

            for msg in deleted_messages:
                author = f"{msg.author.name}#{msg.author.discriminator} ({msg.author.id})".ljust(
                    70
                )
                time = f"{msg.created_at.replace(microsecond=0)}".ljust(30)

                content = f"{msg.content}"
                # TODO save attachments and upload to logging channel
                if msg.attachments:
                    content = "Attachment(s): "
                    for a in msg.attachments:
                        content = f"{content} {a.filename} "

                log_str = f"{log_str} {author} | {time} | {content} \n"

            await message_logging_channel.send(
                f"{len(deleted_messages)} messages deleted in {channel.mention}",
                file=discord.File(
                    io.BytesIO(f"{log_str}".encode()),
                    filename=f"{len(deleted_messages)} messages deleted in {channel.name}.txt",
                ),
            )

        await ctx.message.delete(delay=4)

    @commands.command(aliases=["forceban"])
    @mod_and_above()
    async def fban(self, ctx, member: int, *, reason: str):
        """Force ban a member who is not in the server.\nUsage: fban user_id reason"""
        if reason is None:
            raise commands.BadArgument("Provide a reason and re-run the command")

        logging_channel = discord.utils.get(ctx.guild.channels, id=self.logging_channel)

        # TODO Make helper.create_infraction compatible with IDs
        await ctx.guild.ban(discord.Object(member))

        embed = discord.Embed(
            title="Force Ban",
            description=f"Action By: {ctx.author.mention}",
            color=0xFF0000,
            timestamp=datetime.datetime.utcnow(),
        )
        embed.add_field(name="User(s) Affected ", value=f"{member}", inline=False)
        embed.add_field(name="Reason", value=f"{reason}", inline=False)

        await logging_channel.send(embed=embed)
        await ctx.message.add_reaction("<:kgsYes:955703069516128307>")

        await ctx.message.delete(delay=6)

    @commands.command(aliases=["yeet"])
    @mod_and_above()
    async def ban(self, ctx: commands.Context, inf_level: int, *args):
        """Ban a member.\nUsage: ban infraction_level @member(s) reason"""

        logging_channel = discord.utils.get(ctx.guild.channels, id=self.logging_channel)

        members, extra = custom_converters.get_members(ctx, *args)

        if members is None or members == []:
            raise commands.BadArgument(
                message="Could not find the user please verify if they're still in the server"
            )
        if extra is None:
            raise commands.BadArgument(
                message="Please provide a reason and re-run the command"
            )

        if inf_level not in range(1, 6):
            raise commands.BadArgument(
                message="Infraction level must be between 1 and 5"
            )
        reason = " ".join(extra)

        failed_ban = False
        for m in members:
            if m.top_role < ctx.author.top_role:
                try:
                    await m.send(
                        f"You have been permanently removed from the server for reason: {reason}"
                    )
                except discord.Forbidden:
                    pass
                await m.ban(reason=reason)
            else:
                members.remove(m)
                failed_ban = True
        if failed_ban:
            await ctx.send(
                "Certain users could not be banned due to your clearance",
                delete_after=6,
            )
        if len(members) == 0:
            return

        await ctx.message.add_reaction("<:kgsYes:955703069516128307>")

        helper.create_infraction(
            author=ctx.author,
            users=members,
            action="ban",
            reason=reason,
            inf_level=inf_level,
        )

        embed = helper.create_embed(
            author=ctx.author,
            action="Banned user(s)",
            users=members,
            reason=reason,
            color=discord.Color.dark_red(),
            inf_level=inf_level,
        )

        await logging_channel.send(embed=embed)

        await ctx.message.delete(delay=6)

    @commands.command()
    @mod_and_above()
    async def unban(
        self,
        ctx: commands.Context,
        member_id: commands.Greedy[int] = None,
        *,
        reason: str = None,
    ):
        """Unban a member. \nUsage: unban member_id <reason>"""
        if member_id is None:
            raise commands.BadArgument(message="Invalid member ID provided")

        logging_channel = discord.utils.get(ctx.guild.channels, id=self.logging_channel)

        ban_list = await ctx.guild.bans()

        mem = []  # for listing members in embed

        for b in ban_list:
            if b.user.id in member_id:
                mem.append(b.user)
                if reason is None:
                    reason = b.reason

                await ctx.guild.unban(b.user, reason=reason)
                member_id.remove(b.user.id)

        for m in member_id:
            await ctx.send(f"Member with ID {m} has not been banned before.")

        embed = helper.create_embed(
            author=ctx.author,
            action="Unbanned user(s)",
            users=mem,
            reason=reason,
            color=discord.Color.dark_red(),
        )
        await logging_channel.send(embed=embed)
        await ctx.message.add_reaction("<:kgsYes:955703069516128307>")

    @commands.command()
    @mod_and_above()
    async def kick(self, ctx: commands.Context, inf_level: int, *args):
        """Kick member(s).\nUsage: kick infraction_level @member(s) reason"""

        members, reason = custom_converters.get_members(ctx, *args)

        if reason is None:
            raise commands.BadArgument(
                message="Please provide a reason and re-run the command"
            )

        if inf_level not in range(1, 6):
            raise commands.BadArgument(
                message="Infraction level must be between 1 and 5"
            )

        if members is None:
            raise commands.BadArgument(message="Improper members passed")

        reason = " ".join(reason)
        logging_channel = discord.utils.get(ctx.guild.channels, id=self.logging_channel)

        failed_kick = False
        for i in members:
            if i.top_role < ctx.author.top_role:
                await i.kick(reason=reason)
            else:
                failed_kick = True
                members.remove(i)

        await ctx.message.add_reaction("<:kgsYes:955703069516128307>")
        if failed_kick:
            await ctx.send(
                "Could not kick certain users due to your clearance", delete_after=6
            )
        if len(members) == 0:
            return

        embed = helper.create_embed(
            author=ctx.author,
            action="Kicked User(s)",
            users=members,
            reason=reason,
            color=discord.Color.red(),
            inf_level=inf_level,
        )
        await logging_channel.send(embed=embed)

        helper.create_infraction(
            author=ctx.author,
            users=members,
            action="kick",
            reason=reason,
            inf_level=inf_level,
        )

        await ctx.message.delete(delay=6)

    @commands.command()
    @mod_and_above()
    async def mute(self, ctx: commands.Context, inf_level: int, *args):
        """Mute member(s). \nUsage: mute infraction_level [@member(s) / user_id(s)] <time> reason"""

        tot_time = 0

        logging_channel = discord.utils.get(ctx.guild.channels, id=self.logging_channel)

        members, extra = custom_converters.get_members(ctx, *args)

        if members is None:
            raise commands.BadArgument(message="Improper member passed")
        if inf_level not in range(1, 6):
            raise commands.BadArgument(
                message="Infraction level must be between 1 and 5"
            )

        tot_time, reason = helper.calc_time(extra)

        time_str = "unspecified duration"
        if tot_time is not None:
            time_str = helper.get_time_string(tot_time)

        if reason is None:
            raise commands.BadArgument(
                message="Please provide a reason and re-run the command"
            )

        final_warn = True if reason.startswith("--final") else False
        default_msg = "(Note: Accumulation of warns may lead to permanent removal from the server)"
        if final_warn:
            reason = reason[7:]
            default_msg = "**(This is your final warning, future infractions will lead to a non negotiable ban from the server)**"

        if tot_time > 2419200:
            raise commands.BadArgument(message="Can't mute for longer than 28 days!")
        if tot_time <= 0:
            raise commands.BadArgument(message="Improper time provided")

        failed_mute = False
        for i in members:
            if i.top_role < ctx.author.top_role:
                member_id = i.id
                time = (
                    datetime.datetime.utcnow() + datetime.timedelta(seconds=tot_time)
                ).isoformat()
                route = http.Route(
                    "PATCH", f"/guilds/414027124836532234/members/{member_id}"
                )
                await self.bot.http.request(
                    route, json={"communication_disabled_until": time}, reason=reason
                )

                try:
                    await i.send(
                        f"You have been muted for {time_str}.\nGiven reason: {reason}\n{default_msg}"
                    )

                except discord.Forbidden:
                    pass
            else:
                failed_mute = True
                members.remove(i)

        await ctx.message.add_reaction("<:kgsYes:955703069516128307>")
        if failed_mute:
            await ctx.send(
                "Certain members could not be muted due to your clearance",
                delete_after=6,
            )
        if len(members) == 0:
            return

        embed = helper.create_embed(
            author=ctx.author,
            action="Muted User(s)" + (" (FINAL WARNING)" if final_warn else ""),
            users=members,
            reason=reason,
            extra=f"Mute Duration: {time_str} or {tot_time} seconds",
            color=discord.Color.red(),
            inf_level=inf_level,
        )
        await logging_channel.send(embed=embed)

        helper.create_infraction(
            author=ctx.author,
            users=members,
            action="mute",
            reason=reason,
            time=time_str,
            inf_level=inf_level,
            final_warn=final_warn,
        )

        await ctx.message.delete(delay=6)

    @commands.command()
    @mod_and_above()
    async def unmute(
        self, ctx: commands.Context, members: commands.Greedy[discord.Member]
    ):
        """Unmute member(s). \nUsage: unmute @member(s) <reason>"""

        logging_channel = discord.utils.get(ctx.guild.channels, id=self.logging_channel)

        if not members:
            raise commands.BadArgument(message="Provide members to mute")

        for i in members:
            member_id = i.id
            route = http.Route(
                "PATCH", f"/guilds/414027124836532234/members/{member_id}"
            )
            await self.bot.http.request(
                route, json={"communication_disabled_until": None}
            )

        await ctx.message.add_reaction("<:kgsYes:955703069516128307>")
        embed = helper.create_embed(
            author=ctx.author,
            action="Unmuted User(s)",
            users=members,
            color=discord.Color.red(),
        )

        await logging_channel.send(embed=embed)
        await ctx.message.delete(delay=6)

    @commands.command()
    @mod_and_above()
    async def role(
        self,
        ctx: commands.Context,
        member: discord.Member = None,
        *,
        role_name: str = None,
    ):
        """Add/Remove a role from a member. \nUsage: role @member role_name"""

        logging_channel = discord.utils.get(ctx.guild.channels, id=self.logging_channel)

        if member is None:
            raise commands.BadArgument(message="No members provided")
        if role_name is None:
            raise commands.BadArgument(message="No role provided")

        role = discord.utils.get(ctx.guild.roles, name=role_name)

        if role is None:
            return await ctx.send("Role not found")

        if ctx.author.top_role < role:
            raise commands.BadArgument(message="You don't have clearance to do that")

        r = discord.utils.get(member.roles, name=role.name)
        if r is None:
            await member.add_roles(role)
            await ctx.send(f"Gave role {role.name} to {member.name}")

            embed = helper.create_embed(
                author=ctx.author,
                action="Gave role",
                users=[member],
                extra=f"Role: {role.mention}",
                color=discord.Color.purple(),
            )
            return await logging_channel.send(embed=embed)

        await member.remove_roles(role)
        await ctx.send(f"Removed role {role.name} from {member.name}")
        embed = helper.create_embed(
            author=ctx.author,
            action="Removed role",
            users=[member],
            extra=f"Role: {role.mention}",
            color=discord.Color.purple(),
        )
        return await logging_channel.send(embed=embed)

    @commands.command()
    @mod_and_above()
    async def warn(self, ctx: commands.Context, inf_level: int, *args):
        """Warn user(s) \nUsage: warn infraction_level @member(s) reason"""
        logging_channel = discord.utils.get(ctx.guild.channels, id=self.logging_channel)

        members, reason = custom_converters.get_members(ctx, *args)

        if members is None:
            raise commands.BadArgument(message="No members provided")
        if reason is None:
            raise commands.BadArgument(
                message="No reason provided, please re-run the command with a reaso"
            )

        if inf_level not in range(1, 6):
            raise commands.BadArgument(
                message="Infraction level must be between 1 and 5"
            )

        final_warn = True if reason[0] == "--final" else False
        default_msg = "(Note: Accumulation of warns may lead to permanent removal from the server)"
        if final_warn:
            reason = " ".join(reason[1:])
            default_msg = "**(This is your final warning, future infractions will lead to a non negotiable ban from the server)**"
        else:
            reason = " ".join(reason)

        failed_warn = False
        for m in members:
            if m.top_role.name == "Muted" or m.top_role < ctx.author.top_role:
                try:
                    await m.send(f"You have been warned for {reason} {default_msg}")
                except discord.Forbidden:
                    pass
            else:
                failed_warn = True
                members.remove(m)

        if failed_warn:
            await ctx.send(
                "Certain members could not be warned due to your clearance",
                delete_after=6,
            )
        if len(members) == 0:
            return

        helper.create_infraction(
            author=ctx.author,
            users=members,
            action="warn",
            reason=reason,
            inf_level=inf_level,
            final_warn=final_warn,
        )

        embed = helper.create_embed(
            author=ctx.author,
            action="Warned User(s)" + (" (FINAL WARNING)" if final_warn else ""),
            users=members,
            reason=reason,
            color=discord.Color.red(),
            inf_level=inf_level,
        )
        await logging_channel.send(embed=embed)

        await ctx.message.add_reaction("<:kgsYes:955703069516128307>")
        await ctx.message.delete(delay=6)

    @commands.command(aliases=["unwarn", "removewarn"])
    @mod_and_above()
    async def delwarn(self, ctx: commands.context, member: discord.Member):
        """Remove warn for a user.\nUsage: delwarn @member/id"""
        warns = helper.get_warns(member_id=member.id)

        if warns is None:
            return await ctx.reply("User has no warns.", delete_after=10)

        embed = discord.Embed(
            title=f"Warns for {member.name}",
            description=f"Showing atmost 5 warns at a time. (Total warns: {len(warns)})",
            color=discord.Colour.magenta(),
            timestamp=datetime.datetime.utcnow(),
        )

        warn_len = len(warns)
        page = 0
        start = 0
        end = start + 5 if start + 5 < warn_len else warn_len
        delete_warn_idx = -1

        for idx, warn in enumerate(warns[start:end]):
            embed.add_field(
                name=f"ID: {idx}",
                value="```{0}\n{1}\n{2}```".format(
                    "Author: {} ({})".format(warn["author_name"], warn["author_id"]),
                    "Reason: {}".format(warn["reason"]),
                    "Date: {}".format(warn["datetime"].replace(microsecond=0)),
                ),
                inline=False,
            )

        msg = await ctx.send(embed=embed)

        emote_list = [
            "\u0030\uFE0F\u20E3",
            "\u0031\uFE0F\u20E3",
            "\u0032\uFE0F\u20E3",
            "\u0033\uFE0F\u20E3",
            "\u0034\uFE0F\u20E3",
        ]
        left_arrow = "\u2B05\uFE0F"
        right_arrow = "\u27A1\uFE0F"
        cross = "\u274C"
        yes = "\u2705"

        await msg.add_reaction(left_arrow)
        for i in emote_list[0 : end - start]:
            await msg.add_reaction(i)
        await msg.add_reaction(right_arrow)
        await msg.add_reaction(cross)

        def check(reaction, user):
            return user == ctx.author and (
                str(reaction.emoji) in emote_list
                or str(reaction.emoji) == right_arrow
                or str(reaction.emoji) == left_arrow
                or str(reaction.emoji) == cross
                or str(reaction.emoji) == yes
            )

        try:
            while True:
                reaction, user = await self.bot.wait_for(
                    "reaction_add", timeout=30.0, check=check
                )

                if str(reaction.emoji) in emote_list:
                    await msg.clear_reactions()

                    delete_warn_idx = (page * 5) + emote_list.index(str(reaction.emoji))

                    embed = discord.Embed(
                        title=f"Warns for {member.name}",
                        description=f"Confirm removal of warn",
                        color=discord.Colour.magenta(),
                        timestamp=datetime.datetime.utcnow(),
                    )

                    embed.add_field(
                        name="Delete Warn?",
                        value="```{0}\n{1}\n{2}```".format(
                            "Author: {} ({})".format(
                                warns[delete_warn_idx]["author_name"],
                                warns[delete_warn_idx]["author_id"],
                            ),
                            "Reason: {}".format(warns[delete_warn_idx]["reason"]),
                            "Date: {}".format(
                                warns[delete_warn_idx]["datetime"].replace(
                                    microsecond=0
                                )
                            ),
                        ),
                    )

                    await msg.edit(embed=embed)
                    await msg.add_reaction(yes)
                    await msg.add_reaction(cross)

                elif str(reaction.emoji) == yes:
                    if delete_warn_idx != -1:

                        del warns[delete_warn_idx]
                        helper.update_warns(member.id, warns)

                        await msg.edit(
                            content="Warning deleted successfully.",
                            embed=None,
                            delete_after=5,
                        )
                        break

                elif str(reaction.emoji) == cross:
                    await msg.edit(content="Exited!!!", embed=None, delete_after=5)
                    break

                else:
                    await msg.clear_reactions()

                    if str(reaction.emoji) == left_arrow:
                        if page >= 1:
                            page -= 1

                    elif str(reaction.emoji) == right_arrow:
                        if page < (warn_len - 1) // 5:
                            page += 1

                    start = page * 5
                    end = start + 5 if start + 5 < warn_len else warn_len

                    embed = discord.Embed(
                        title=f"Warns for {member.name}",
                        description=f"Showing atmost 5 warns at a time",
                        color=discord.Colour.magenta(),
                        timestamp=datetime.datetime.utcnow(),
                    )
                    for idx, warn in enumerate(warns[start:end]):
                        embed.add_field(
                            name=f"ID: {idx}",
                            value="```{0}\n{1}\n{2}```".format(
                                "Author: {} ({})".format(
                                    warn["author_name"], warn["author_id"]
                                ),
                                "Reason: {}".format(warn["reason"]),
                                "Date: {}".format(
                                    warn["datetime"].replace(microsecond=0)
                                ),
                            ),
                            inline=False,
                        )

                    await msg.edit(embed=embed)

                    await msg.add_reaction(left_arrow)
                    for i in emote_list[0 : end - start]:
                        await msg.add_reaction(i)
                    await msg.add_reaction(right_arrow)
                    await msg.add_reaction(cross)

        except asyncio.TimeoutError:
            await msg.clear_reactions()
            await ctx.message.delete(delay=5)
            return

        await ctx.message.delete(delay=5)

    @commands.command(aliases=["infr", "inf", "infraction"])
    @mod_and_above()
    async def infractions(
        self,
        ctx: commands.Context,
        member: typing.Optional[discord.Member] = None,
        mem_id: typing.Optional[int] = None,
        inf_type: str = None,
    ):
        """Get Infractions. \nUsage: infr <@member / member_id> <infraction_type>"""
        try:

            if member is None and mem_id is None:
                return await ctx.send(
                    "Provide user.\n`Usage: infr <@member / member_id> <infraction_type>`"
                )

            if inf_type is not None:
                if (
                    inf_type == "w"
                    or inf_type == "W"
                    or re.match("warn", inf_type, re.IGNORECASE)
                ):
                    inf_type = "warn"
                elif (
                    inf_type == "m"
                    or inf_type == "M"
                    or re.match("mute", inf_type, re.IGNORECASE)
                ):
                    inf_type = "mute"
                elif (
                    inf_type == "b"
                    or inf_type == "B"
                    or re.match("ban", inf_type, re.IGNORECASE)
                ):
                    inf_type = "ban"
                elif (
                    inf_type == "k"
                    or inf_type == "K"
                    or re.match("kick", inf_type, re.IGNORECASE)
                ):
                    inf_type = "kick"

            else:
                inf_type = "warn"

            if member is not None:
                mem_id = member.id

            infs_embed = helper.get_infractions(member_id=mem_id, inf_type=inf_type)

            msg = None
            msg = await ctx.send(embed=infs_embed)
            await msg.add_reaction("\U0001F1FC")
            await msg.add_reaction("\U0001F1F2")
            await msg.add_reaction("\U0001F1E7")
            await msg.add_reaction("\U0001F1F0")

            while True:
                try:
                    reaction, user = await self.bot.wait_for(
                        "reaction_add",
                        check=lambda reaction, user: user == ctx.author
                        and reaction.emoji
                        in [
                            "\U0001F1FC",
                            "\U0001F1F2",
                            "\U0001F1E7",
                            "\U0001F1F0",
                        ],
                        timeout=20.0,
                    )

                except asyncio.exceptions.TimeoutError:
                    if msg:
                        await msg.clear_reactions()
                    break

                else:
                    em = reaction.emoji
                    if em == "\U0001F1FC":
                        inf_type = "warn"
                        infs_embed = helper.get_infractions(
                            member_id=mem_id, inf_type=inf_type
                        )
                        await msg.edit(embed=infs_embed)
                        await msg.remove_reaction(emoji=em, member=user)

                    elif em == "\U0001F1F2":
                        inf_type = "mute"
                        infs_embed = helper.get_infractions(
                            member_id=mem_id, inf_type=inf_type
                        )
                        await msg.edit(embed=infs_embed)
                        await msg.remove_reaction(emoji=em, member=user)

                    elif em == "\U0001F1E7":
                        inf_type = "ban"
                        infs_embed = helper.get_infractions(
                            member_id=mem_id, inf_type=inf_type
                        )
                        await msg.edit(embed=infs_embed)
                        await msg.remove_reaction(emoji=em, member=user)

                    elif em == "\U0001F1F0":
                        inf_type = "kick"
                        infs_embed = helper.get_infractions(
                            member_id=mem_id, inf_type=inf_type
                        )
                        await msg.edit(embed=infs_embed)
                        await msg.remove_reaction(emoji=em, member=user)

        except asyncio.exceptions.TimeoutError:
            await ctx.send("Embed Timed Out.", delete_after=3.0)
            if msg:
                await msg.clear_reactions()

    @commands.command(aliases=["dinfr", "inf_details","infr_details", "details"])
    @mod_and_above()
    async def detailed_infr(
        self,
        ctx: commands.Context,
        user: typing.Optional[discord.User],
        infr_type: str,
        infr_id: int,
    ):
        """Get detailed single Infractions. \nUsage: dinfr <@member / member_id> w/m/k/b infraction_id"""

        infr_type = infr_type.lower()

        if infr_type not in ["w", "b", "m", "k"]:
            return await ctx.reply("Infraction can only be any of these: w, m, k, b")

        if infr_type == "w":
            infr_type = "warn"
        elif infr_type == "m":
            infr_type = "mute"
        elif infr_type == "b":
            infr_type = "ban"
        else:
            infr_type = "kick"

        result = get_single_infraction_type(user.id, infr_type)

        if result == -1:
            await ctx.reply("Invalid command format.", delete_after=6)
            await ctx.message.add_reaction("<:kgsNo:955703108565098496>")

        elif result:

            if infr_id not in range(0, len(result)):
                await ctx.message.add_reaction("<:kgsNo:955703108565098496>")
                return await ctx.reply("Invalid infraction ID.", delete_after=6)

            result = result[infr_id]
            embed = discord.Embed(
                title=f"Detailed infraction for {user.name} ({user.id}) ",
                description=f"**Infraction Type:** {infr_type}",
                color=discord.Color.green(),
                timestamp=datetime.datetime.utcnow(),
            )
            embed.add_field(
                name=f"Author", value=f"<@{result['author_id']}>", inline=False
            )
            embed.add_field(
                name="Date (UTC)",
                value=result["datetime"].replace(microsecond=0),
                inline=False,
            )
            embed.add_field(name="Base Reason", value=result["reason"], inline=False)
            if "infraction_level" in result:
                embed.add_field(
                    name="Infraction Level",
                    value=result["infraction_level"],
                    inline=False,
                )
                del result["infraction_level"]

            del (
                result["author_id"],
                result["author_name"],
                result["datetime"],
                result["reason"],
            )

            for key in result:
                embed.add_field(name=key, value=result[key], inline=False)

            await ctx.send(embed=embed)
            await ctx.message.add_reaction("<:kgsYes:955703069516128307>")

    @commands.command(aliases=["einf", "einfr", "edit_infr", "editinfr"])
    @mod_and_above()
    async def edit_infraction(
        self,
        ctx: commands.Context,
        user: discord.User,
        infr_type: str,
        infr_id: int,
        title: str,
        *,
        description: str,
    ):
        """Add details to an infraction. \nUsage: edit_infr @user/id w/m/k/b infraction_id title description"""

        infr_type = infr_type.lower()

        if infr_type not in ["w", "b", "m", "k"]:
            return await ctx.reply("Infraction can only be any of these: w, m, k, b")

        if infr_type == "w":
            infr_type = "warn"
        elif infr_type == "m":
            infr_type = "mute"
        elif infr_type == "b":
            infr_type = "ban"
        else:
            infr_type = "kick"

        result = append_infraction(user.id, infr_type, infr_id, title, description)

        if result == -1:
            await ctx.reply(
                "Infraction with given id and type not found.", delete_after=6
            )
            await ctx.message.add_reaction("<:kgsNo:955703108565098496>")

        else:
            await ctx.message.add_reaction("<:kgsYes:955703069516128307>")
            await ctx.reply("Infraction updated successfully.", delete_after=6)

            extra = f"Title: {title}\nDescription: {description} \nID: {infr_id}"

            embed = helper.create_embed(
                author=ctx.author,
                action=f"Appended details to {infr_type} ",
                users=[user],
                extra=extra,
                color=discord.Color.red(),
            )

            logging_channel = discord.utils.get(
                ctx.guild.channels, id=self.logging_channel
            )
            await logging_channel.send(embed=embed)

    @commands.command(aliases=["slothmode"])
    @mod_and_above()
    async def slowmode(
        self,
        ctx: commands.Context,
        time=None,
        channel: typing.Optional[discord.TextChannel] = None,
        *,
        reason: str = None,
    ):
        """Add/Remove slowmode. \nUsage: slowmode <slowmode_time> <#channel> <reason>"""

        time = calc_time([time, ""])[0]

        if time is None:
            time = 0

        if time > 21600:
            raise commands.BadArgument(message="Slowmode can't be over 6 hours.")

        ch = ctx.channel

        if channel is not None:
            ch = channel

        await ch.edit(slowmode_delay=time, reason=reason)

        logging_channel = discord.utils.get(ctx.guild.channels, id=self.logging_channel)
        embed = helper.create_embed(
            author=ctx.author,
            action="Added slow mode.",
            users=None,
            reason=reason,
            extra=f"Channel: {ch.mention}\nSlowmode Duration: {time} seconds",
            color=discord.Color.orange(),
        )
        await logging_channel.send(embed=embed)

        await ctx.send(f"Slowmode of {time}s added to {ch.mention}.")

    @commands.command(aliases=["blacklist_command", "commandblacklist"])
    @mod_and_above()
    async def nocmd(self, ctx, member: discord.Member, command_name: str):
        """
        Blacklists a member from a command
        Usage: nocmd @user/user_ID command_name
        """

        command = discord.utils.get(self.bot.commands, name=command_name)
        if command is None:
            raise commands.BadArgument(message=f"{command_name} is not a valid command")
        if ctx.author.top_role > member.top_role:
            blacklist_member(self.bot, member, command)
            await ctx.send(f"{member.name} can no longer use {command_name}")
        else:
            await ctx.send(f"You cannot blacklist someone higher or equal to you smh")

    @commands.command(aliases=["whitelist_command", "commandwhitelist"])
    @mod_and_above()
    async def yescmd(self, ctx, member: discord.Member, command_name: str):
        """
        Whitelists a member from a command
        Usage: yescmd @user/user_ID command_name
        """
        command = discord.utils.get(self.bot.commands, name=command_name)
        if command is None:
            raise commands.BadArgument(message=f"{command_name} is not a valid command")
        if whitelist_member(member, command):
            await ctx.send(f"{member.name} can now use {command.name}")
        else:
            await ctx.send(f"{member.name} is not blacklisted from {command.name}")


def setup(bot):
    bot.add_cog(Moderation(bot))
