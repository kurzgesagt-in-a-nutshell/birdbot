import json
import io
import re
import typing
import datetime
import asyncio
import logging

from utils import helper
from utils.helper import helper_and_above, mod_and_above, patreon_only

from utils import custom_converters

import discord
from discord.ext import commands, tasks


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger("Moderation")
        self.bot = bot

        self.timed_action_list = helper.get_timed_actions()

        config_file = open("config.json", "r")
        self.config_json = json.loads(config_file.read())
        config_file.close()

        self.logging_channel = self.config_json["logging"]["logging_channel"]
        self.mod_role = self.config_json["roles"]["mod_role"]
        self.admin_role = self.config_json["roles"]["admin_role"]
        self.patreon_roles = [
            self.config_json["roles"]["patreon_blue_role"],
            self.config_json["roles"]["patreon_green_role"],
            self.config_json["roles"]["patreon_orange_role"],
        ]

    @tasks.loop(minutes=10.0)
    async def timed_action_loop(self):
        guild = discord.utils.get(self.bot.guilds, id=414027124836532234)
        mute_role = discord.utils.get(
            guild.roles, id=self.config_json["roles"]["mute_role"]
        )
        logging_channel = discord.utils.get(guild.channels, id=self.logging_channel)

        for action in self.timed_action_list:
            if action["action_end"] < datetime.datetime.utcnow():
                user = discord.utils.get(guild.members, id=action["user_id"])

                if user is not None:
                    await user.remove_roles(mute_role, reason="Time Expired")

                helper.delete_timed_actions_uid(u_id=action["user_id"])

                embed = discord.Embed(
                    title="Timed Action",
                    description="Time Expired",
                    color=discord.Color.dark_blue(),
                    timestamp=datetime.datetime.utcnow(),
                )
                embed.add_field(
                    name="User Affected",
                    value="{} ({})".format(action["user_name"], action["user_id"]),
                    inline=False,
                )
                embed.add_field(
                    name="Action",
                    value="Un{}".format(action["action"]),
                    inline=False,
                )
                await logging_channel.send(embed=embed)

        self.timed_action_list = helper.get_timed_actions()

    @commands.Cog.listener()
    async def on_ready(self):
        self.timed_action_loop.start()
        self.logger.info("loaded Moderation")

    def cog_unload(self):
        self.timed_action_loop.cancel()

    # Listen for new patreons
    @commands.Cog.listener()
    async def on_member_join(self, member):
        diff_roles = [role.id for role in member.roles]
        if any(x in diff_roles for x in self.patreon_roles):

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
                    url="https://cdn.discordapp.com/emojis/824253681443536896.png?size=96"
                )

                await member.send(embed=embed)
            except discord.Forbidden:
                return

    # Remind mods to use the correct prefix
    @commands.Cog.listener()
    async def on_message(self, message):
        guild = discord.utils.get(self.bot.guilds, id=414027124836532234)
        mod_role = discord.utils.get(guild.roles, id=self.mod_role)
        admin_role = discord.utils.get(guild.roles, id=self.admin_role)

        if not any(role in message.author.roles for role in (mod_role, admin_role)):
            return
        if re.match("^-(kick|ban|mute)", message.content):
            await message.channel.send(f"ahem.. {message.author.mention}")

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

        logging_channel = discord.utils.get(ctx.guild.channels, id=self.logging_channel)

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

            await logging_channel.send(embed=embed)

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

            await logging_channel.send(
                f"{len(deleted_messages)} messages deleted in {channel.mention}",
                file=discord.File(
                    io.BytesIO(f"{log_str}".encode()),
                    filename=f"{len(deleted_messages)} messages deleted in {channel.name}.txt",
                ),
            )

        await ctx.message.delete(delay=4)

    @commands.command(aliases=["yeet"])
    @mod_and_above()
    async def ban(self, ctx: commands.Context, *args):
        """Ban a member.\nUsage: ban @member(s) reason"""

        logging_channel = discord.utils.get(ctx.guild.channels, id=self.logging_channel)

        members, extra = custom_converters.get_members(ctx, *args)

        if members is None or members == []:
            raise commands.BadArgument(message="Improper members passed")
        if extra is None:
            raise commands.BadArgument(
                message="Please provide a reason and re-run the command"
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
            x = await ctx.send(
                "Certain users could not be banned due to your clearance"
            )
        if len(members) == 0:
            return

        await ctx.message.add_reaction("<:kgsYes:580164400691019826>")

        helper.create_infraction(
            author=ctx.author, users=members, action="ban", reason=reason
        )

        embed = helper.create_embed(
            author=ctx.author,
            action="Banned user(s)",
            users=members,
            reason=reason,
            color=discord.Color.dark_red(),
        )

        await logging_channel.send(embed=embed)

        await asyncio.sleep(6)
        await ctx.message.delete()
        await x.delete()

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
        await ctx.message.add_reaction("<:kgsYes:580164400691019826>")

    @commands.command()
    @mod_and_above()
    async def kick(self, ctx: commands.Context, *args):
        """Kick member(s).\nUsage: kick @member(s) reason"""

        members, reason = custom_converters.get_members(ctx, *args)

        if reason is None:
            raise commands.BadArgument(
                message="Please provide a reason and re-run the command"
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

        await ctx.message.add_reaction("<:kgsYes:580164400691019826>")
        if failed_kick:
            x = await ctx.send("Could not kick certain users due to your clearance")
        if len(members) == 0:
            return

        embed = helper.create_embed(
            author=ctx.author,
            action="Kicked User(s)",
            users=members,
            reason=reason,
            color=discord.Color.red(),
        )
        await logging_channel.send(embed=embed)

        helper.create_infraction(
            author=ctx.author, users=members, action="kick", reason=reason
        )

        await asyncio.sleep(6)
        await ctx.message.delete()
        await x.delete()

    @commands.command()
    @helper_and_above()
    async def mute(self, ctx: commands.Context, *args):
        """Mute member(s). \nUsage: mute @member(s) <time> reason"""

        tot_time = 0
        is_muted = False

        logging_channel = discord.utils.get(ctx.guild.channels, id=self.logging_channel)
        mute_role = discord.utils.get(
            ctx.guild.roles, id=self.config_json["roles"]["mute_role"]
        )

        members, extra = custom_converters.get_members(ctx, *args)

        if members is None:
            raise commands.BadArgument(message="Improper member passed")

        tot_time, reason = helper.calc_time(extra)

        time_str = "unspecified duration"
        if tot_time is not None:
            time_str = helper.get_time_string(tot_time)

        if reason is None:
            raise commands.BadArgument(
                message="Please provide a reason and re-run the command"
            )

        failed_mute = False
        for i in members:
            if i.top_role < ctx.author.top_role:
                await i.add_roles(mute_role, reason=reason)
                try:
                    await i.send(
                        f"You have been muted for {time_str}.\nGiven reason: {reason}\n"
                        "(Note: Accumulation of mutes may lead to permanent removal from the server)"
                    )

                except discord.Forbidden:
                    pass
            else:
                failed_mute = True
                members.remove(i)

        await ctx.message.add_reaction("<:kgsYes:580164400691019826>")
        if failed_mute:
            x = await ctx.send(
                "Certain members could not be muted due to your clearance"
            )
        if len(members) == 0:
            return

        is_muted = True

        embed = helper.create_embed(
            author=ctx.author,
            action="Muted User(s)",
            users=members,
            reason=reason,
            extra=f"Mute Duration: {time_str} or {tot_time} seconds",
            color=discord.Color.red(),
        )
        await logging_channel.send(embed=embed)

        helper.create_infraction(
            author=ctx.author,
            users=members,
            action="mute",
            reason=reason,
            time=time_str,
        )

        if is_muted:
            if tot_time != 0:
                # TIMED
                helper.create_timed_action(users=members, action="mute", time=tot_time)

                self.timed_action_list = helper.get_timed_actions()

        await asyncio.sleep(6)
        await ctx.message.delete()
        await x.delete()

    @commands.command()
    @helper_and_above()
    async def unmute(
        self, ctx: commands.Context, members: commands.Greedy[discord.Member]
    ):
        """Unmute member(s). \nUsage: unmute @member(s) <reason>"""

        logging_channel = discord.utils.get(ctx.guild.channels, id=self.logging_channel)

        if not members:
            raise commands.BadArgument(message="Provide members to mute")

        mute_role = discord.utils.get(
            ctx.guild.roles, id=self.config_json["roles"]["mute_role"]
        )
        for i in members:
            await i.remove_roles(mute_role, reason=f"Unmuted by {ctx.author}")
            # TIMED
            helper.delete_timed_actions_uid(u_id=i.id)
            self.timed_action_list = helper.get_timed_actions()

        await ctx.message.add_reaction("<:kgsYes:580164400691019826>")
        embed = helper.create_embed(
            author=ctx.author,
            action="Unmuted User(s)",
            users=members,
            color=discord.Color.red(),
        )

        await logging_channel.send(embed=embed)
        await asyncio.sleep(6)
        await ctx.message.delete()

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
    @helper_and_above()
    async def warn(self, ctx: commands.Context, *args):
        """Warn user(s) \nUsage: warn @member(s) reason"""
        logging_channel = discord.utils.get(ctx.guild.channels, id=self.logging_channel)

        members, reason = custom_converters.get_members(ctx, *args)

        if members is None:
            raise commands.BadArgument(message="No members provided")
        if reason is None:
            raise commands.BadArgument(
                message="No reason provided, please re-run the command with a reaso"
            )

        reason = " ".join(reason)

        failed_warn = False
        for m in members:
            if m.top_role.name == "Muted" or m.top_role < ctx.author.top_role:
                try:
                    await m.send(
                        f"You have been warned for {reason} (Note: Accumulation of warns may lead to permanent removal from the server)"
                    )
                except discord.Forbidden:
                    pass
            else:
                failed_warn = True
                members.remove(m)

        if failed_warn:
            x = await ctx.send(
                "Certain members could not be warned due to your clearance"
            )
        if len(members) == 0:
            return

        helper.create_infraction(
            author=ctx.author, users=members, action="warn", reason=reason
        )

        embed = helper.create_embed(
            author=ctx.author,
            action="Warned User(s)",
            users=members,
            reason=reason,
            color=discord.Color.red(),
        )
        await logging_channel.send(embed=embed)

        await ctx.message.add_reaction("<:kgsYes:580164400691019826>")
        await asyncio.sleep(6)
        await ctx.message.delete()
        if failed_warn:
            await x.delete()

    @commands.command(aliases=["unwarn", "removewarn"])
    @mod_and_above()
    async def delwarn(self, ctx: commands.context, member: discord.Member):
        """Remove warn for a user.\nUsage: delwarn @member/id"""
        warns = helper.get_warns(member_id=member.id)

        if warns is None:
            return await ctx.send("User has no warns.")

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
                        # await msg.delete(delay=5)
                        break

                elif str(reaction.emoji) == cross:
                    await msg.edit(content="Exited!!!", embed=None, delete_after=5)
                    # await msg.delete(delay=5)
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
                    await ctx.send("Embed Timed Out.", delete_after=3.0)
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

    @commands.command(aliases=["slothmode"])
    @mod_and_above()
    async def slowmode(
        self,
        ctx: commands.Context,
        time: typing.Optional[int] = None,
        channel: typing.Optional[discord.TextChannel] = None,
        *,
        reason: str = None,
    ):
        """Add/Remove slowmode. \nUsage: slowmode <slowmode_time> <#channel> <reason>"""

        if time is None:
            time = 0

        if time < 0:
            raise commands.BadArgument(message="Improper time provided")

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


def setup(bot):
    bot.add_cog(Moderation(bot))
