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
from utils import helper, app_checks, app_errors
from utils.helper import (
    append_infraction,
    bot_commands_only,
    devs_only,
    get_single_infraction_type,
    mod_and_above,
    calc_time,
    get_active_staff,
    blacklist_member,
    whitelist_member,
    is_public_channel
)

import discord
from discord.ext import commands, tasks
from discord import app_commands


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

    # TODO OPEN THIS COMMAND FOR REGULAR USERS AND ENABLE ACTIVE MOD PING
    @app_commands.command()
    @app_commands.guilds(414027124836532234)
    @app_checks.devs_only()
    async def report(
        self, 
        interaction: discord.Interaction, 
        member: typing.Optional[discord.Member]
    ):  
        """
        This command is currently locked please use `!report` to report an incident
        """
        
        class Modal(discord.ui.Modal):
            def __init__(self, member):
                super().__init__(title="Report")
                self.member = member

            text = discord.ui.TextInput(
                label="Briefly describe your issue",
                style=discord.TextStyle.long,
            )
            message = discord.ui.TextInput(
                label="Message link",
                style=discord.TextStyle.short,
                placeholder="https://discord.com/channels/414027124836532234/414268041787080708/937750299165208607",
                required=False,
            )

            async def on_submit(self, interaction):
                description = self.children[0].value
                message_link = self.children[1].value

                mod_embed = discord.Embed(
                    title="New Report", 
                    color=0x00FF00,
                    description=f"""
                    **Report description:** {description}
                    **User:** {self.member}
                    **Message Link:** [click to jump]({message_link})
                    """
                )
                mod_embed.set_author(
                    name=f"{interaction.user.name} ({interaction.user.id})", 
                    icon_url=interaction.user.display_avatar.url
                )

                mod_channel = interaction.guild.get_channel(414095428573986816)
                await mod_channel.send(embed=mod_embed)

                await interaction.response.send_message(
                    "Report has been sent!", ephemeral=True
                )

        await interaction.response.send_modal(Modal(member=member))

    @app_commands.command(name="clean")
    @app_commands.guilds(414027124836532234)
    @app_checks.mod_and_above()
    @app_commands.rename(_from="from")
    async def _clean(
        self,
        interaction: discord.Interaction,
        limit: app_commands.Range[int, 1, 100],
        _from: typing.Optional[discord.User], 
        channel: typing.Union[discord.TextChannel, discord.Thread, None] = None
    ):
        """Cleans messages with certain parameters"""

        if channel is None: 
            channel = interaction.channel

        def check(message):
            if _from is not None and _from.id == message.author.id:
                return True
            return False

        deleted_messages = await channel.purge(
            limit=limit, 
            check=check,
            bulk=limit!=1 # if count is 1 then dont bulk delete
        )

        deleted_count = len(deleted_messages)

        await interaction.response.send_message(
            f"deleted {deleted_count} messages{'s' if deleted_count > 1 else ''}",
            ephemeral=True
        )

        # no need to manually log a single delete
        if limit == 1: return

        # format the log
        row_format = lambda x: "{author:<70} | {datetime:<20} | {content}".format(**x)

        message_log = [row_format({
            "author":"Author (ID)",
            "datetime": "Message Creation Time (UTC)",
            "content": "Content"
        })]

        # TODO save attachments and upload to logging channel
        for m in deleted_messages:
            author = f"{m.author.name}#{m.author.discriminator} ({m.author.id})"
            
            content = m.content
            if m.attachments and len(m.attachments) > 0:
                attachments = "; ".join(f.filename for f in m.attachments)
                content = f"Attachments Included: {attachments}; {content}"
            
            message_log.append(row_format({
                "author": author,
                "datetime": f"{m.created_at.replace(microsecond=0)}",
                "content": content
            }))

        message_logging_channel = discord.utils.get(
            interaction.guild.channels, id=self.message_logging_channel
        )

        await message_logging_channel.send(
            f"{len(deleted_messages)} messages deleted in {channel.mention}",
            file=discord.File(
                io.BytesIO("\n".join(message_log).encode()),
                filename=f"clean_content_{interaction.id}.txt",
            )
        )

    @app_commands.command(name="ban")
    @app_commands.guilds(414027124836532234)
    @app_commands.default_permissions(manage_messages=True)
    @app_checks.mod_and_above()
    async def _ban(
        self, 
        interaction: discord.Interaction,
        inf_level:app_commands.Range[int, 1, 5],
        user: discord.User,
        reason:str
    ):
        """Bans a member"""
        
        if member:=await interaction.guild.fetch_member(user.id) is not None:
            if member.top_role >= interaction.user.top_role:
            
                raise app_errors.InvalidAuthorizationError(
                    "user could not be banned due to your clearance"
                )

            try:
                await member.send(
                    f"You have been permanently removed from the server for reason: {reason}"
                )
            except discord.Forbidden:
                pass
        
        # await member.ban(reason=reason)
        await interaction.channel.send(f"I would ban {user.name} here")

        helper.create_infraction(
            author=interaction.user,
            users=[member],
            action="ban",
            reason=reason,
            inf_level=inf_level,
        )

        logging_channel = discord.utils.get(interaction.guild.channels, id=self.logging_channel)

        embed = helper.create_embed(
            author=interaction.user,
            action="Banned user(s)",
            users=[member],
            reason=reason,
            color=discord.Color.dark_red(),
            inf_level=inf_level,
        )

        await logging_channel.send(embed=embed)

        await interaction.response.send_message(
            "user has been banned", 
            ephemeral=is_public_channel(interaction.channel)
        )

    @app_commands.command(name="unban")
    @app_commands.guilds(414027124836532234)
    @app_commands.default_permissions(manage_messages=True)
    @app_checks.mod_and_above()
    async def _unban(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        reason: typing.Optional[str] = None
    ):
        """Unban a member"""

        try:
            # await interaction.guild.unban(user, reason=reason)
            await interaction.channel.send("I would unban here")
        except discord.NotFound:
            await interaction.response.send_message(
                f"User <@{id}> has not been banned before.",
                ephemeral=is_public_channel(interaction.channel)
            )
            return

        logging_channel = discord.utils.get(interaction.guild.channels, id=self.logging_channel)

        embed = helper.create_embed(
            author=interaction.user,
            action="Unbanned user(s)",
            users=[user],
            reason=reason,
            color=discord.Color.dark_red(),
        )
        await logging_channel.send(embed=embed)

        await interaction.response.send_message(
            "user was unbanned", 
            ephemeral=is_public_channel(interaction.channel)
        )

    @app_commands.command(name="kick")
    @app_commands.guilds(414027124836532234)
    @app_commands.default_permissions(manage_messages=True)
    @app_checks.mod_and_above()
    async def _kick(
        self,
        interaction: discord.Interaction,
        inf_level: app_commands.Range[int, 1, 5],
        member: discord.Member,
        reason: str
    ):
        """Kicks a member"""

        if member.top_role >= interaction.user.top_role:
            
            raise app_errors.InvalidAuthorizationError(
                "user could not be kicked due to your clearance"
            )

        # await member.kick(reason=reason)
        await interaction.channel.send("I would kick here")

        helper.create_infraction(
            author=interaction.user,
            users=[member],
            action="kick",
            reason=reason,
            inf_level=inf_level,
        )

        logging_channel = discord.utils.get(interaction.guild.channels, id=self.logging_channel)

        embed = helper.create_embed(
            author=interaction.user,
            action="Kicked User(s)",
            users=[member],
            reason=reason,
            color=discord.Color.red(),
            inf_level=inf_level,
        )
        await logging_channel.send(embed=embed)

        await interaction.response.send_message(
            "member has been kicked", 
            ephemeral=is_public_channel(interaction.channel)
        )
    
    @app_commands.command(name="selfmute")
    @app_commands.guilds(414027124836532234)
    async def _selfmute(
        self,
        interaction: discord.Interaction,
        time: str,
        reason: typing.Optional[str] = "Self Mute"
    ):
        """Mute yourself"""

        tot_time, _ = helper.calc_time([time, ""])

        if tot_time is None or tot_time <= 0:
            raise app_errors.InvalidInvocationError(
                "Improper time provided"
            )
        elif tot_time > 604801:
            raise app_errors.InvalidInvocationError(
                "Can't mute for longer than 7 days!"
            )
        elif tot_time < 300:
            raise app_errors.InvalidInvocationError(
                "Can't mute for shorter than 5 minutes!"
            )

        duration = datetime.timedelta(seconds=tot_time)
        finished = discord.utils.utcnow() + duration

        time_str = helper.get_time_string(tot_time)

        await interaction.user.timeout(finished)

        await interaction.response.send_message(
            f"""
            You have been self muted for {time_str} until <t:{int(finished.timestamp())}>.
            Given reason: {reason}
            mods will not unmute you :) think twice about doing the command next time
            """,
            ephemeral=True
        )

        logging_channel = discord.utils.get(interaction.guild.channels, id=713107972737204236)

        embed = helper.create_embed(
            author=interaction.user,
            action="Self Mute",
            users=[interaction.user],
            reason=reason,
            extra=f"Mute Duration: {tot_time}",
            color=discord.Color.red(),
            inf_level=0,
        )

        await logging_channel.send(embed=embed)

    @app_commands.command(name="mute")
    @app_commands.guilds(414027124836532234)
    @app_commands.default_permissions(manage_messages=True)
    @app_checks.mod_and_above()
    async def _mute(
        self,
        interaction: discord.Interaction,
        inf_level: app_commands.Range[int, 1, 5],
        member: discord.Member,
        time: str,
        reason: str,
        final: typing.Optional[bool] = False
    ):
        """Mutes a member"""

        if member.top_role >= interaction.user.top_role:

            raise app_errors.InvalidAuthorizationError(
                "user could not be muted due to your clearance"
            )

        # time calculation
        tot_time, _ = helper.calc_time([time, ""])

        if tot_time is None:
            raise app_errors.InvalidInvocationError(
                "no valid time provided"
            )
        elif tot_time <= 0:
            raise app_errors.InvalidInvocationError(
                "time can not be 0 or less"
            )
        elif tot_time > 2419200:
            raise app_errors.InvalidInvocationError(
                "time can not be longer than 28 days (2419200 seconds)"
            )

        duration = datetime.timedelta(seconds=tot_time)
        finished = discord.utils.utcnow() + duration

        time_str = helper.get_time_string(tot_time)


        default_msg = "(Note: Accumulation of warns may lead to permanent removal from the server)"
        final_msg = "**(This is your final warning, future infractions will lead to a non negotiable ban from the server)**"
        if final:
            default_msg = final_msg

        try:
            await member.send(
                f"You have been muted for {time_str}.\nGiven reason: {reason}\n{default_msg}"
            )
        except discord.Forbidden:
            pass

        await member.timeout(finished)

        helper.create_infraction(
            author=interaction.user,
            users=[member],
            action="mute",
            reason=reason,
            time=time_str,
            inf_level=inf_level,
            final_warn=final,
        )

        logging_channel = discord.utils.get(interaction.guild.channels, id=self.logging_channel)

        embed = helper.create_embed(
            author=interaction.user,
            action="Muted User(s)" + (" (FINAL WARNING)" if final else ""),
            users=[member],
            reason=reason,
            extra=f"Mute Duration: {time_str} or {tot_time} seconds",
            color=discord.Color.red(),
            inf_level=inf_level,
        )
        await logging_channel.send(embed=embed)

        await interaction.response.send_message(
            "member has been muted", 
            ephemeral=is_public_channel(interaction.channel)
        )

    @app_commands.command(name="unmute")
    @app_commands.guilds(414027124836532234)
    @app_commands.default_permissions(manage_messages=True)
    @app_checks.mod_and_above()
    async def _unmute(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: typing.Optional[str]
    ):
        """Unmutes a member"""

        logging_channel = discord.utils.get(interaction.guild.channels, id=self.logging_channel)

        await member.timeout(None)

        embed = helper.create_embed(
            author=interaction.user,
            action="Unmuted User(s)",
            users=[member],
            color=discord.Color.red(),
        )

        await logging_channel.send(embed=embed)

        await interaction.response.send_message(
            "member has been unmuted", 
            ephemeral=is_public_channel(interaction.channel)
        )

    @app_commands.command(name="role")
    @app_commands.guilds(414027124836532234)
    @app_commands.default_permissions(manage_messages=True)
    @app_checks.mod_and_above()
    async def _role(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        role: discord.Role
    ):
        """Add/Remove a role from a member"""

        if role >= interaction.user.top_role:

            raise app_errors.InvalidAuthorizationError(
                "you do not have clearance to do that"
            )

        # check if member has role
        action, preposition = "", ""
        if role in member.roles:
            # remove role
            await member.remove_roles(role)
            action = "Removed role"
            preposition = "from"
        else:
            # add role
            await member.add_roles(role)
            action = "Gave role"
            preposition = "to"

        logging_channel = discord.utils.get(interaction.guild.channels, id=self.logging_channel)

        embed = helper.create_embed(
            author=interaction.user,
            action=action,
            users=[member],
            extra=f"Role: {role.mention}",
            color=discord.Color.purple(),
        )
        await logging_channel.send(embed=embed)

        await interaction.response.send_message(
            f"{action.lower()} {role.name} {preposition} {member.name}", 
            ephemeral=is_public_channel(interaction.channel),
            allowed_mentions=discord.AllowedMentions.none()
        )

    @app_commands.command(name="warn")
    @app_commands.guilds(414027124836532234)
    @app_commands.default_permissions(manage_messages=True)
    @app_checks.mod_and_above()
    async def _warn(
        self,
        interaction: discord.Interaction,
        inf_level: app_commands.Range[int, 1, 5],
        member: discord.Member,
        reason: str,
        final: typing.Optional[bool] = False
    ):
        """Warns a user"""

        if member.top_role >= interaction.user.top_role:

            raise app_errors.InvalidAuthorizationError(
                "user could not be warned due to your clearance"
            )

        # TODO make this more modular
        default_msg = "(Note: Accumulation of warns may lead to permanent removal from the server)"
        final_msg = "**(This is your final warning, future infractions will lead to a non negotiable ban from the server)**"
        if final:
            default_msg = final_msg

        try:
            await member.send(f"You have been warned for {reason} {default_msg}")
        except discord.Forbidden:
            pass

        helper.create_infraction(
            author=interaction.user,
            users=[member],
            action="warn",
            reason=reason,
            inf_level=inf_level,
            final_warn=final,
        )

        logging_channel = discord.utils.get(interaction.guild.channels, id=self.logging_channel)

        embed = helper.create_embed(
            author=interaction.user,
            action="Warned User(s)" + (" (FINAL WARNING)" if final else ""),
            users=[member],
            reason=reason,
            color=discord.Color.red(),
            inf_level=inf_level,
        )
        await logging_channel.send(embed=embed)

        await interaction.response.send_message(
            "user has been warned", 
            ephemeral=is_public_channel(interaction.channel)
        )

    # TODO CONVERT THIS COMMAND
    @commands.command(aliases=["unwarn", "removewarn"])
    @mod_and_above()
    async def delwarn(self, ctx: commands.context, member: discord.Member):      
        class View(discord.ui.View):
            def __init__(self, warns):
                super().__init__(timeout=20)
                self.delete_warn_idx = -1
                self.page = 0
                self.warns = warns
                self.warn_len = len(warns)

                for i in range(5):
                    disabled=False
                    if i >= self.warn_len:
                        disabled = True
                    self.add_item(Button(label=str(i), disabled=disabled))

            @discord.ui.button(label="<", style=discord.ButtonStyle.blurple, row=1)
            async def back(self, button: discord.ui.Button, interaction: discord.Interaction):
                self.delete_warn_idx = -1
                if self.page >= 1:
                    self.page -= 1
                else:
                    self.page = (self.warn_len - 1) // 5
                await self.write_msg(interaction)
            @discord.ui.button(label=">", style=discord.ButtonStyle.blurple, row=1)
            async def forward(self, button: discord.ui.Button, interaction: discord.Interaction):
                self.delete_warn_idx = -1
                if self.page < (self.warn_len - 1) // 5:
                    self.page += 1
                else:
                    self.page = 0
                await self.write_msg(interaction)
            @discord.ui.button(label="x", style=discord.ButtonStyle.red, row=1)
            async def exit(self, button: discord.ui.Button, interaction: discord.Interaction):
                await interaction.message.edit(content="Exited!!!", embed=None, view=None, delete_after=5)
                self.stop()
                return
            @discord.ui.button(label="✓", style=discord.ButtonStyle.green, row=1, disabled=True)
            async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction):
                if self.delete_warn_idx != -1:

                    del self.warns[self.delete_warn_idx]
                    helper.update_warns(member.id, self.warns)

                    await interaction.message.edit(
                        content="Warning deleted successfully.",
                        embed=None,
                        view=None,
                        delete_after=5,
                    )
                    self.stop()
                return

            async def write_msg(self, interaction):
                delete_warn_idx = self.delete_warn_idx
                page = self.page
                warn_len = self.warn_len

                embed = discord.Embed(
                    title=f"Warns for {member.name}",
                    color=discord.Colour.magenta(),
                    timestamp=discord.utils.utcnow(),
                )

                if delete_warn_idx != -1:
                    embed.description=f"Confirm removal of warn"
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
                    for button in self.children:
                        if button.label == "✓":
                            button.disabled=False
                        elif button.row == 0:
                            button.disabled=True
                else:
                    start = page * 5
                    end = start + 5 if start + 5 < warn_len else warn_len

                    for button in self.children:
                        if button.row == 0:
                            if int(button.label) >= (end - start):
                                button.disabled=True
                            else:
                                button.disabled=False
                        elif button.label == "✓":
                            button.disabled=True

                    embed.description=f"Showing atmost 5 warns at a time. (Total warns: {warn_len})"
                    embed.set_footer(text=f"Page {page+1}/{(warn_len-1)//5+1}")

                    for idx, warn in enumerate(self.warns[start:end]):
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

                await interaction.message.edit(embed=embed, view=view)


            async def on_timeout(self):
                await msg.edit(view=None, delete_after=5)

            async def interaction_check(self, interaction):
                if interaction.user == ctx.author:
                    return True
                else:
                    await interaction.response.send_message(
                        "You can't use that", ephemeral=True
                    )

        class Button(discord.ui.Button):
            def __init__(self, label, disabled):
                super().__init__(label=label, style=discord.ButtonStyle.gray, row=0, disabled=disabled)

            async def callback(self, interaction: discord.Interaction):
                view.delete_warn_idx = int(self.label)
                await view.write_msg(interaction)
                return

        warns = helper.get_warns(member_id=member.id)
        #warns might not get deleted properly, temp fix
        if warns is None or warns == []:
            return await ctx.reply("User has no warns.", delete_after=10)

        view = View(warns=warns)

        warn_len = len(warns)

        embed = discord.Embed(
            title=f"Warns for {member.name}",
            description=f"Showing atmost 5 warns at a time. (Total warns: {warn_len})",
            color=discord.Colour.magenta(),
            timestamp=discord.utils.utcnow(),
        )
        embed.set_footer(text=f"Page 1/{(warn_len-1)//5+1}")
        
        end = 5 if 5 < warn_len else warn_len
        
        for idx, warn in enumerate(warns[0:end]):
            embed.add_field(
                name=f"ID: {idx}",
                value="```{0}\n{1}\n{2}```".format(
                    "Author: {} ({})".format(warn["author_name"], warn["author_id"]),
                    "Reason: {}".format(warn["reason"]),
                    "Date: {}".format(warn["datetime"].replace(microsecond=0)),
                ),
                inline=False,
            )
        msg = await ctx.send(embed=embed, view=view)

    @app_commands.command(name="infractions")
    @app_commands.guilds(414027124836532234)
    @app_commands.default_permissions(manage_messages=True)
    @app_checks.mod_and_above()
    async def _infractions(
        self,
        interaction: discord.Interaction,
        user: discord.User
    ):
        """
        Checks a users infractions. Allows the checking of infractions of
        members not currently in the server. Prioritizes user_id if both user
        and user_id are provided.
        """

        class InfButton(discord.ui.Button):
            """
            Represents a button to switch pages on an infraction embed view
            """
            
            def __init__(self, label, inf_type, **kwargs):
                super().__init__(label=label, **kwargs)
                self.inf_type = inf_type

            async def callback(self, interaction):
                
                infs_embed = helper.get_infractions(
                    member_id=user.id, 
                    inf_type=self.inf_type
                )
                # might need to utilize this if original message is ephemeral
                # https://discordpy.readthedocs.io/en/latest/interactions/api.html#discord.Interaction.edit_original_message
                await interaction.response.edit_message(embed=infs_embed)

        class InfractionView(discord.ui.View):
            """
            Represents an infraction embed view
            """

            def __init__(self, initial_interaction: discord.Interaction):
                super().__init__(timeout=60)

                self.interaction = initial_interaction

                self.add_item(InfButton(label="Warns", inf_type="warn"))
                self.add_item(InfButton(label="Mutes", inf_type="mute"))
                self.add_item(InfButton(label="Bans", inf_type="ban"))
                self.add_item(InfButton(label="Kicks", inf_type="kick"))

            async def on_timeout(self):
                """Remove view"""

                await self.interaction.edit_original_message(view=None)

        infs_embed = helper.get_infractions(member_id=user.id, inf_type="warn")

        await interaction.response.send_message(
            embed=infs_embed, 
            view=InfractionView(interaction),
            ephemeral=is_public_channel(interaction.channel)
        )

    # TODO CONVERT THIS COMMAND
    @commands.command(aliases=["dinfr", "inf_details", "infr_details", "details"])
    @mod_and_above()
    async def detailed_infr(
        self,
        ctx: commands.Context,
        user: typing.Optional[discord.User],
        infr_type: str,
        infr_id: int,
    ):
        """Get detailed single Infractions. \nUsage: dinfr @member/member_id w/m/k/b infraction_id"""

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
                timestamp=discord.utils.utcnow(),
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

    # TODO CONVERT THIS COMMAND
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

        await ctx.message.delete(delay=6)

    @app_commands.command(name="slowmode")
    @app_commands.guilds(414027124836532234)
    @app_commands.default_permissions(manage_messages=True)
    @app_checks.mod_and_above()
    async def _slowmode(
        self,
        interaction: discord.Interaction,
        time: str,
        channel: typing.Union[discord.TextChannel, discord.Thread, None],
        reason: typing.Optional[str]
    ):
        """Add or remove slowmode in a channel"""

        seconds, _ = helper.calc_time(time)

        if seconds is None:
            seconds = 0

        if seconds > 21600:
            await interaction.response.send_message(
                "Slowmode can't be over 6 hours",
                ephemeral=True
            )
            return

        if channel is None:
            channel = interaction.channel

        await channel.edit(slowmode_delay=seconds, reason=reason)

        logging_channel = discord.utils.get(interaction.guild.channels, id=self.logging_channel)
        embed = helper.create_embed(
            author=interaction.user,
            action="Added slow mode.",
            users=None,
            reason=reason,
            extra=f"Channel: {channel.mention}\nSlowmode Duration: {seconds} seconds",
            color=discord.Color.orange(),
        )
        await logging_channel.send(embed=embed)

        await interaction.response.send_message(
            f"slowmode of {seconds} seconds added to {channel.mention}.", 
            ephemeral=True
        )

    # TODO CONVERT THIS COMMAND
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

    # TODO CONVERT THIS COMMAND
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


async def setup(bot):
    await bot.add_cog(Moderation(bot))
