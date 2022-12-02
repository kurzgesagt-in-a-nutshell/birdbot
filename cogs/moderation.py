import json
import io
import typing
import datetime
import logging


from utils import helper, app_checks, app_errors
from utils.helper import (
    append_infraction,
    get_single_infraction_type,
    get_active_staff,
    blacklist_member,
    whitelist_member,
    is_public_channel,
)

import discord
from discord.ext import commands
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

    @app_commands.command()
    @app_commands.checks.cooldown(1, 30)
    async def report(
        self,
        interaction: discord.Interaction,
        member: typing.Optional[typing.Union[discord.Member, discord.User]] = None,
    ):
        """Report issues to the moderation team, gives you an UI

        Parameters
        ----------
        member: discord.Member
            Mention or ID of member to report (is optional)
        """

        if interaction.guild:
            mod_channel = interaction.guild.get_channel(414095428573986816)
        else:
            kgs_guild = self.bot.get_guild(414027124836532234)
            mod_channel = await kgs_guild.fetch_channel(414095428573986816)

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
                    """,
                )
                mod_embed.set_author(
                    name=f"{interaction.user.name} ({interaction.user.id})",
                    icon_url=interaction.user.display_avatar.url,
                )

                await mod_channel.send(
                    get_active_staff(interaction.client), embed=mod_embed
                )

                await interaction.response.send_message(
                    "Report has been sent!", ephemeral=True
                )

        await interaction.response.send_modal(Modal(member=member))

    @app_commands.command()
    @app_commands.guilds(414027124836532234)
    @app_checks.mod_and_above()
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.rename(_from="from")
    async def clean(
        self,
        interaction: discord.Interaction,
        count: app_commands.Range[int, 1, 200],
        _from: typing.Optional[discord.Member],
        channel: typing.Union[discord.TextChannel, discord.Thread, None] = None,
    ):
        """Cleans/Purge messages from a channel

        Parameters
        ----------
        count: int
            Number of messages to clear
        from: discord.Member
            If provided, deletes all messages from this user from last "count" messages
        channel: discord.TextChannel
            Channel from which messages needs to be deleted (default: current channel)
        """

        if channel is None:
            channel = interaction.channel

        await interaction.response.defer(ephemeral=True)

        def check(message):
            # Note:
            # This is conditional to check if the `message` is the interaction message that invoked the clean command.
            # The purge function works perfectly regardless of this conditional, but commenting it if it's needed in future.
            # if message.interaction and interaction.id == message.interaction.id:
            #     return False

            if _from is None or _from.id == message.author.id:
                return True
            return False

        deleted_messages = await channel.purge(
            limit=count,
            check=check,
            bulk=count != 1,  # if count is 1 then dont bulk delete
        )

        deleted_count = len(deleted_messages)

        await interaction.edit_original_response(
            content=f"Deleted {deleted_count} message{'s' if deleted_count > 1 else ''}{f' from {_from.mention}' if _from else ''} in channel {channel.mention}",
        )

        # format the log
        row_format = lambda x: "{author:<70} | {datetime:<20} | {content}".format(**x)

        message_log = [
            row_format(
                {
                    "author": "Author (ID)",
                    "datetime": "Message Creation Time (UTC)",
                    "content": "Content",
                }
            )
        ]

        # TODO save attachments and upload to logging channel
        for m in deleted_messages:
            author = f"{m.author.name}#{m.author.discriminator} ({m.author.id})"

            content = m.content
            if m.attachments and len(m.attachments) > 0:
                attachments = "; ".join(f.filename for f in m.attachments)
                content = f"Attachments Included: {attachments}; {content}"

            message_log.append(
                row_format(
                    {
                        "author": author,
                        "datetime": f"{m.created_at.replace(microsecond=0)}",
                        "content": content,
                    }
                )
            )

        message_logging_channel = discord.utils.get(
            interaction.guild.channels, id=self.message_logging_channel
        )

        await message_logging_channel.send(
            f"{len(deleted_messages)} messages deleted in {channel.mention}",
            file=discord.File(
                io.BytesIO("\n".join(message_log).encode()),
                filename=f"clean_content_{interaction.id}.txt",
            ),
        )

    @app_commands.command()
    @app_commands.guilds(414027124836532234)
    @app_commands.default_permissions(manage_messages=True)
    @app_checks.mod_and_above()
    async def ban(
        self,
        interaction: discord.Interaction,
        inf_level: app_commands.Range[int, 1, 5],
        user: discord.User,
        reason: str,
    ):
        """Ban or Force ban a user

        Parameters
        ----------
        inf_level: int
            Infraction level
        user: discord.User
            User mention or ID to ban (Provide ID to force ban)
        reason: str
            Reason for the action
        """

        try:
            # fetch_member throws not_found error if not found
            member = await interaction.guild.fetch_member(user.id)
            if member.top_role >= interaction.user.top_role:
                raise app_errors.InvalidAuthorizationError(
                    "User could not be banned due to your clearance."
                )

            await member.send(
                f"You have been permanently removed from the server for following reason: \n{reason}"
            )
        except (discord.NotFound, discord.Forbidden):
            pass

        await interaction.guild.ban(user=user, reason=reason)

        await interaction.response.send_message(
            "User has been banned", ephemeral=is_public_channel(interaction.channel)
        )

        helper.create_infraction(
            author=interaction.user,
            users=[user],
            action="ban",
            reason=reason,
            inf_level=inf_level,
        )

        logging_channel = discord.utils.get(
            interaction.guild.channels, id=self.logging_channel
        )

        embed = helper.create_embed(
            author=interaction.user,
            action="Banned user(s)",
            users=[user],
            reason=reason,
            color=discord.Color.dark_red(),
            inf_level=inf_level,
        )

        await logging_channel.send(embed=embed)

    @app_commands.command()
    @app_commands.guilds(414027124836532234)
    @app_commands.default_permissions(manage_messages=True)
    @app_checks.mod_and_above()
    async def unban(
        self,
        interaction: discord.Interaction,
        user_id: discord.User,
        reason: typing.Optional[str] = None,
    ):
        """Unban a user

        Parameters
        ----------
        user_id: discord.User
            User's ID
        reason: str
            Reason for the action
        """

        try:
            await interaction.guild.unban(user_id, reason=reason)
        except discord.NotFound:
            await interaction.response.send_message(
                f"User has not been banned before.",
                ephemeral=is_public_channel(interaction.channel),
            )
            return

        await interaction.response.send_message(
            "user was unbanned", ephemeral=is_public_channel(interaction.channel)
        )

        logging_channel = discord.utils.get(
            interaction.guild.channels, id=self.logging_channel
        )

        embed = helper.create_embed(
            author=interaction.user,
            action="Unbanned user(s)",
            users=[user_id],
            reason=reason,
            color=discord.Color.dark_red(),
        )
        await logging_channel.send(embed=embed)

    @app_commands.command()
    @app_commands.guilds(414027124836532234)
    @app_commands.default_permissions(manage_messages=True)
    @app_checks.mod_and_above()
    async def kick(
        self,
        interaction: discord.Interaction,
        inf_level: app_commands.Range[int, 1, 5],
        member: discord.Member,
        reason: str,
    ):
        """Kick a user

        Parameters
        ----------
        inf_level: int
            Infraction level
        member: discord.Member
            User mention or ID
        reason: str
            Reason for the action
        """

        if member.top_role >= interaction.user.top_role:

            raise app_errors.InvalidAuthorizationError(
                "User could not be kicked due to your clearance."
            )

        await member.kick(reason=reason)

        await interaction.response.send_message(
            "member has been kicked", ephemeral=is_public_channel(interaction.channel)
        )

        helper.create_infraction(
            author=interaction.user,
            users=[member],
            action="kick",
            reason=reason,
            inf_level=inf_level,
        )

        logging_channel = discord.utils.get(
            interaction.guild.channels, id=self.logging_channel
        )

        embed = helper.create_embed(
            author=interaction.user,
            action="Kicked User(s)",
            users=[member],
            reason=reason,
            color=discord.Color.red(),
            inf_level=inf_level,
        )
        await logging_channel.send(embed=embed)

    @app_commands.command()
    @app_commands.guilds(414027124836532234)
    @app_commands.checks.cooldown(1, 60)
    async def selfmute(
        self,
        interaction: discord.Interaction,
        time: str,
        reason: typing.Optional[str] = "Self Mute",
    ):
        """Mute yourself.

        Parameters
        ----------
        time: str
            Duration of mute (min 5 mins, max 7 days). Use suffix "s", "m", "h", "d" along with time. (ex 3m, 5h, 1d)
        reason: str
            Reason for the action
        """

        tot_time, _ = helper.calc_time([time, ""])

        if tot_time is None or tot_time <= 0:
            raise app_errors.InvalidInvocationError("Improper time provided")
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
            ephemeral=True,
        )

        logging_channel = discord.utils.get(
            interaction.guild.channels, id=713107972737204236
        )

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

    @app_commands.command()
    @app_commands.guilds(414027124836532234)
    @app_commands.default_permissions(manage_messages=True)
    @app_checks.mod_and_above()
    async def mute(
        self,
        interaction: discord.Interaction,
        inf_level: app_commands.Range[int, 1, 5],
        member: discord.Member,
        time: str,
        reason: str,
        final: typing.Optional[bool] = False,
    ):
        """Mute a user

        Parameters
        ----------
        inf_level: int
            Infraction level
        member: discord.Member
            Member mention or ID
        reason: str
            Reason for the action
        """

        if member.top_role >= interaction.user.top_role:

            raise app_errors.InvalidAuthorizationError(
                "user could not be muted due to your clearance"
            )

        # time calculation
        tot_time, _ = helper.calc_time([time, ""])

        if tot_time is None:
            raise app_errors.InvalidInvocationError("no valid time provided")
        elif tot_time <= 0:
            raise app_errors.InvalidInvocationError("time can not be 0 or less")
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

        await interaction.response.send_message(
            "member has been muted", ephemeral=is_public_channel(interaction.channel)
        )

        helper.create_infraction(
            author=interaction.user,
            users=[member],
            action="mute",
            reason=reason,
            time=time_str,
            inf_level=inf_level,
            final_warn=final,
        )

        logging_channel = discord.utils.get(
            interaction.guild.channels, id=self.logging_channel
        )

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

    @app_commands.command()
    @app_commands.guilds(414027124836532234)
    @app_commands.default_permissions(manage_messages=True)
    @app_checks.mod_and_above()
    async def unmute(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: typing.Optional[str],
    ):
        """Unmutes a user

        Parameters
        ----------
        member: discord.Member
            Member mention or ID
        reason: str
            Reason for the action
        """

        logging_channel = discord.utils.get(
            interaction.guild.channels, id=self.logging_channel
        )

        await member.timeout(None)

        embed = helper.create_embed(
            author=interaction.user,
            action="Unmuted User(s)",
            users=[member],
            color=discord.Color.red(),
            reason=reason,
        )

        await logging_channel.send(embed=embed)

        await interaction.response.send_message(
            "member has been unmuted", ephemeral=is_public_channel(interaction.channel)
        )

    @app_commands.command()
    @app_commands.guilds(414027124836532234)
    @app_commands.default_permissions(manage_messages=True)
    @app_checks.mod_and_above()
    async def role(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        role: discord.Role,
    ):
        """Add or Remove role to/from a user

        Parameters
        ----------
        member: discord.Member
            Member mention or ID
        role: discord.Role
            Role to add or remove
        """

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

        await interaction.response.send_message(
            f"{action.lower()} {role.name} {preposition} {member.name}",
            ephemeral=is_public_channel(interaction.channel),
            allowed_mentions=discord.AllowedMentions.none(),
        )

        logging_channel = discord.utils.get(
            interaction.guild.channels, id=self.logging_channel
        )

        embed = helper.create_embed(
            author=interaction.user,
            action=action,
            users=[member],
            extra=f"Role: {role.mention}",
            color=discord.Color.purple(),
        )
        await logging_channel.send(embed=embed)

    @app_commands.command()
    @app_commands.guilds(414027124836532234)
    @app_commands.default_permissions(manage_messages=True)
    @app_checks.mod_and_above()
    async def warn(
        self,
        interaction: discord.Interaction,
        inf_level: app_commands.Range[int, 1, 5],
        member: discord.Member,
        reason: str,
        final: typing.Optional[bool] = False,
    ):
        """Warns a user

        Parameters
        ----------
        inf_level: int
            Infraction level
        member: discord.Member
            Member mention or ID
        reason: str
            Reason for the action
        final: bool
            Mark warn as final
        """

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

        await interaction.response.send_message(
            "user has been warned", ephemeral=is_public_channel(interaction.channel)
        )

        helper.create_infraction(
            author=interaction.user,
            users=[member],
            action="warn",
            reason=reason,
            inf_level=inf_level,
            final_warn=final,
        )

        logging_channel = discord.utils.get(
            interaction.guild.channels, id=self.logging_channel
        )

        embed = helper.create_embed(
            author=interaction.user,
            action="Warned User(s)" + (" (FINAL WARNING)" if final else ""),
            users=[member],
            reason=reason,
            color=discord.Color.red(),
            inf_level=inf_level,
        )
        await logging_channel.send(embed=embed)

    @app_commands.command()
    @app_commands.guilds(414027124836532234)
    @app_commands.default_permissions(manage_messages=True)
    @app_checks.mod_and_above()
    async def delwarn(self, interaction: discord.Interaction, member: discord.Member):
        """Delete a warn of a user

        Parameters
        ----------
        member: discord.Member
            Member mention or ID
        """

        class View(discord.ui.View):
            def __init__(self, warns):
                super().__init__(timeout=20)
                self.delete_warn_idx = -1
                self.page = 0
                self.warns = warns
                self.warn_len = len(warns)

                for i in range(5):
                    disabled = False
                    if i >= self.warn_len:
                        disabled = True
                    self.add_item(Button(label=str(i), disabled=disabled))

            @discord.ui.button(label="<", style=discord.ButtonStyle.blurple, row=1)
            async def back(
                self, interaction: discord.Interaction, button: discord.ui.Button
            ):
                self.delete_warn_idx = -1
                if self.page >= 1:
                    self.page -= 1
                else:
                    self.page = (self.warn_len - 1) // 5
                await self.write_msg(interaction)

            @discord.ui.button(label=">", style=discord.ButtonStyle.blurple, row=1)
            async def forward(
                self, interaction: discord.Interaction, button: discord.ui.Button
            ):
                self.delete_warn_idx = -1
                if self.page < (self.warn_len - 1) // 5:
                    self.page += 1
                else:
                    self.page = 0
                await self.write_msg(interaction)

            @discord.ui.button(label="x", style=discord.ButtonStyle.red, row=1)
            async def exit(
                self, interaction: discord.Interaction, button: discord.ui.Button
            ):
                await interaction.message.edit(
                    content="Exited!!!", embed=None, view=None, delete_after=5
                )
                self.stop()
                return

            @discord.ui.button(
                label="✓", style=discord.ButtonStyle.green, row=1, disabled=True
            )
            async def confirm(
                self, interaction: discord.Interaction, button: discord.ui.Button
            ):
                if self.delete_warn_idx != -1:

                    del self.warns[self.page * 5 + self.delete_warn_idx]
                    helper.update_warns(member.id, self.warns)

                    await interaction.response.edit_message(
                        content="Warning deleted successfully.", embed=None, view=None
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
                    warn_idx = page * 5 + delete_warn_idx
                    embed.description = f"Confirm removal of warn"
                    embed.add_field(
                        name="Delete Warn?",
                        value="```{0}\n{1}\n{2}```".format(
                            "Author: {} ({})".format(
                                warns[warn_idx]["author_name"],
                                warns[warn_idx]["author_id"],
                            ),
                            "Reason: {}".format(warns[warn_idx]["reason"]),
                            "Date: {}".format(
                                warns[warn_idx]["datetime"].replace(microsecond=0)
                            ),
                        ),
                    )
                    for button in self.children:
                        if button.label == "✓":
                            button.disabled = False
                        elif button.row == 0:
                            button.disabled = True
                else:
                    start = page * 5
                    end = start + 5 if start + 5 < warn_len else warn_len

                    for button in self.children:
                        if button.row == 0:
                            if int(button.label) >= (end - start):
                                button.disabled = True
                            else:
                                button.disabled = False
                        elif button.label == "✓":
                            button.disabled = True

                    embed.description = (
                        f"Showing atmost 5 warns at a time. (Total warns: {warn_len})"
                    )
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

                await interaction.response.edit_message(embed=embed, view=view)

            async def on_timeout(self):
                """Removes the view on timeout"""

                await interaction.edit_original_response(view=None)

            async def interaction_check(self, new_interaction):
                if new_interaction.user.id == interaction.user.id:
                    return True
                else:
                    await interaction.response.send_message(
                        "You can't use that", ephemeral=True
                    )

        class Button(discord.ui.Button):
            def __init__(self, label, disabled):
                super().__init__(
                    label=label,
                    style=discord.ButtonStyle.gray,
                    row=0,
                    disabled=disabled,
                )

            async def callback(self, interaction: discord.Interaction):
                view.delete_warn_idx = int(self.label)
                await view.write_msg(interaction)
                return

        warns = helper.get_warns(member_id=member.id)
        # warns might not get deleted properly, temp fix
        if warns is None or warns == []:
            return await interaction.response.send_message(
                "User has no warns.", ephemeral=True
            )

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
        await interaction.response.send_message(
            embed=embed, view=view, ephemeral=is_public_channel(interaction.channel)
        )

    @app_commands.command()
    @app_commands.guilds(414027124836532234)
    @app_commands.default_permissions(manage_messages=True)
    @app_checks.mod_and_above()
    async def infractions(self, interaction: discord.Interaction, user: discord.User):
        """Checks a users infractions.

        Parameters
        ----------
        user: discord.User
            User mention or user id

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
                    member_id=user.id, inf_type=self.inf_type
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
                """
                Removes the view on timeout for visual aid
                """

                await self.interaction.edit_original_response(view=None)

        infs_embed = helper.get_infractions(member_id=user.id, inf_type="warn")

        await interaction.response.send_message(
            embed=infs_embed,
            view=InfractionView(interaction),
            ephemeral=is_public_channel(interaction.channel),
        )

    @app_commands.command()
    @app_commands.guilds(414027124836532234)
    @app_commands.default_permissions(manage_messages=True)
    @app_checks.mod_and_above()
    async def detailed_infr(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        infr_type: typing.Literal["warn", "ban", "mute", "kick"],
        infr_id: int,
    ):
        """Get detailed view of an infraction.

        Parameters
        ----------
        user: discord.User
            User mention or user id
        infr_type: str
            Type of infraction "warn", "ban", "mute", "kick"
        infr_id: int
            ID as mentioned as last field of the infraction
        """

        result = get_single_infraction_type(user.id, infr_type)

        if result == -1:
            await interaction.response.send_message(
                "Invalid command format.",
                ephemeral=is_public_channel(interaction.channel),
            )
            return

        elif result:

            if infr_id not in range(0, len(result)):
                await interaction.response.send_message(
                    "Invalid infraction ID.",
                    ephemeral=is_public_channel(interaction.channel),
                )
                return

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

            await interaction.response.send_message(
                embed=embed, ephemeral=is_public_channel(interaction.channel)
            )

    @app_commands.command()
    @app_commands.guilds(414027124836532234)
    @app_commands.default_permissions(manage_messages=True)
    @app_checks.mod_and_above()
    async def editinfr(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        infr_type: typing.Literal["warn", "ban", "mute", "kick"],
        infr_id: int,
        title: str,
        description: str,
    ):
        """Add extra fields to an infractions

        Parameters
        ----------
        user: discord.User
            User or User ID
        infr_type: str
            Type of infractions "warn", "ban", "mute", "kick"
        infr_id: int
            ID as mentioned as last field of the infraction
        title: str
            Title for the field
        description: str
            Description for the field
        """

        result = append_infraction(user.id, infr_type, infr_id, title, description)

        if result == -1:
            await interaction.response.send_message(
                "Infraction with given id and type not found.", ephemeral=True
            )
            return

        else:

            await interaction.response.send_message(
                "Infraction updated successfully.",
                ephemeral=is_public_channel(interaction.channel),
            )

            extra = f"Title: {title}\nDescription: {description} \nID: {infr_id}"

            embed = helper.create_embed(
                author=interaction.user,
                action=f"Appended details to {infr_type} ",
                users=[user],
                extra=extra,
                color=discord.Color.red(),
            )

            logging_channel = discord.utils.get(
                interaction.guild.channels, id=self.logging_channel
            )
            await logging_channel.send(embed=embed)

    @app_commands.command()
    @app_commands.guilds(414027124836532234)
    @app_commands.default_permissions(manage_messages=True)
    @app_checks.mod_and_above()
    async def slowmode(
        self,
        interaction: discord.Interaction,
        duration: app_commands.Range[int, 0, 360],
        channel: typing.Union[discord.TextChannel, discord.Thread, None],
        reason: typing.Optional[str],
    ):
        """Add or remove slowmode in a channel

        Parameters
        -----------
        duration: int
            Duration in seconds (0 - 360), 0 to remove slowmode
        channel: discord.TextChannel
            Channel to enable slowmode (default: current channel)
        reason: str
            Reason for the action
        """

        if channel is None:
            channel = interaction.channel

        await channel.edit(slowmode_delay=duration, reason=reason)

        await interaction.response.send_message(
            f"slowmode of {duration} seconds added to {channel.mention}.",
            ephemeral=True,
        )

        logging_channel = discord.utils.get(
            interaction.guild.channels, id=self.logging_channel
        )

        embed = helper.create_embed(
            author=interaction.user,
            action="Added slow mode.",
            users=None,
            reason=reason,
            extra=f"Channel: {channel.mention}\nSlowmode Duration: {duration} seconds",
            color=discord.Color.orange(),
        )
        await logging_channel.send(embed=embed)

    @app_commands.command()
    @app_commands.guilds(414027124836532234)
    @app_commands.default_permissions(manage_messages=True)
    @app_checks.mod_and_above()
    async def nocmd(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        command_name: str,
    ):
        """
        Blacklists a member from using a command

        Parameters
        ----------
        member: discord.Member
            Member or Member ID
        command_name: str
            command to blacklist
        """

        command = discord.utils.get(self.bot.commands, name=command_name)
        if command is None:
            return await interaction.response.send_message(
                f"{command_name} is not a valid command", ephemeral=True
            )
        if interaction.user.top_role > member.top_role:
            blacklist_member(self.bot, member, command)
            await interaction.response.send_message(
                f"{member.name} can no longer use {command_name}", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"You cannot blacklist someone higher or equal to you smh.",
                ephemeral=True,
            )

    @app_commands.command()
    @app_commands.guilds(414027124836532234)
    @app_commands.default_permissions(manage_messages=True)
    @app_checks.mod_and_above()
    async def yescmd(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        command_name: str,
    ):
        """
        Whitelist a member from using a command

        Parameters
        ----------
        member: discord.Member
            Member or Member ID
        command_name: str
            command to whitelist
        """
        command = discord.utils.get(self.bot.commands, name=command_name)
        if command is None:
            return await interaction.response.send_message(
                f"{command_name} is not a valid command", ephemeral=True
            )
        if whitelist_member(member, command):
            await interaction.response.send_message(
                f"{member.name} can now use {command.name}", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"{member.name} is not blacklisted from {command.name}", ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(Moderation(bot))
