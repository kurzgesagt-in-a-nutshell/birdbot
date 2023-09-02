import json
import io
import typing
import datetime
import logging


from app.utils import helper, checks, errors
from app.utils.helper import (
    get_active_staff,
    blacklist_member,
    whitelist_member,
    is_public_channel,
)
from app.utils.infraction import InfractionList, InfractionKind
from app.utils.config import Reference

import discord
from discord.ext import commands
from discord import app_commands


class FinalReconfirmation(discord.ui.View):
    """
    This view handles the interaction with moderators to confirm action while a
    user is on final warn. The moderator can choose to continue with the action
    or to cancel the action and follow through with a more appropriate action.

    The moderator is also given the option to cancel while timing the user out
    for 10 minutes to provide decision making time.
    """

    @classmethod
    async def handle(
        cls,
        interaction: discord.Interaction,
        infractions: InfractionList,
        user: discord.Member,
        moderator: discord.Member,
    ):
        """
        Manages the action of the reconfirmation and returns once the action is
        complete. Returns -1 if the action is to be canceled and 1 if the action
        is to proceed.

        # the state change must be made before the call to stop
        """

        reconfirmation = cls(user, moderator)

        # BECAUSE OF THIS INTERACTION, COMMANDS THAT USE THIS VIEW MUST USE
        # MAYBE RESPONDED LOGIC
        await interaction.response.send_message(
            f"{user.mention} is on final warning. Confirm action or cancel...",
            ephemeral=is_public_channel(interaction.channel),
            view=reconfirmation,
        )

        failed = await reconfirmation.wait()
        if failed:
            reconfirmation.state = -1

        return reconfirmation.state

    def __init__(self, user: discord.Member, moderator: discord.Member):
        super().__init__(timeout=2 * 60)

        self.user = user
        self.moderator = moderator

        self.state = 0

    async def interaction_check(self, interaction: discord.Interaction):
        """
        Checks that the user interacting with this is the moderator that issued
        the warn.
        """

        return interaction.user.id == self.moderator.id

    @discord.ui.button(label="Continue", style=discord.ButtonStyle.danger)
    async def _continue(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Removes the view and edits the message to inform that the action will
        continue
        """

        self.state = 1
        self.stop()

        await interaction.response.edit_message(
            content=f"Action on {self.user.mention} will continue",
            view=None,
            allowed_mentions=None,
        )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey, row=2)
    async def _cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Removes the view to prevent more actions and edits the message to
        display the choice made
        """

        self.state = -1
        self.stop()

        await interaction.response.edit_message(
            content=f"Action on {self.user.mention} is canceled",
            view=None,
            allowed_mentions=None,
        )

    @discord.ui.button(label="10m Timeout", style=discord.ButtonStyle.blurple)
    async def _timeout(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Times out the user for 10 minutes to allow for further decision making.
        This does not record an infraction but allows the moderator to take time
        to think.
        """

        self.state = -1
        self.stop()

        await self.user.timeout(datetime.timedelta(minutes=10), reason="user timed out for decision making")

        await interaction.response.edit_message(
            content=f"{self.user.mention} was muted for 10 minutes to allow for decision making",
            view=None,
            allowed_mentions=None,
        )


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger("Moderation")
        self.bot = bot

        self.logging_channel = Reference.Channels.Logging.mod_actions
        self.message_logging_channel = Reference.Channels.Logging.message_actions
        self.mod_role = Reference.Roles.moderator
        self.admin_role = Reference.Roles.administrator

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
            mod_channel = interaction.guild.get_channel(Reference.Channels.mod_chat)
        else:
            kgs_guild = self.bot.get_guild(Reference.guild)
            mod_channel = await kgs_guild.fetch_channel(Reference.Channels.mod_chat)

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

            async def on_submit(self, interaction: discord.Interaction):
                description = self.children[0].value
                message_link = self.children[1].value

                channel = interaction.channel
                if isinstance(channel, (discord.abc.GuildChannel, discord.Thread)):
                    channel_mention = channel.mention

                    # What this does is allow you to click the link to go to the
                    # messages around the time the report was made
                    if message_link is None or message_link == "":
                        message_link = f"https://discord.com/channels/414027124836532234/{channel.id}/{interaction.id}"

                else:
                    channel_mention = "Sent through DMs"

                mod_embed = discord.Embed(
                    title="New Report",
                    color=0x00FF00,
                    description=f"""
                    **Report description:** {description}
                    **User:** {self.member}
                    **Message Link:** [click to jump]({message_link})
                    **Reported in:** {channel_mention}
                    """,
                )
                mod_embed.set_author(
                    name=f"{interaction.user.name} ({interaction.user.id})",
                    icon_url=interaction.user.display_avatar.url,
                )

                await mod_channel.send(
                    get_active_staff(interaction.client),
                    embed=mod_embed,
                    allowed_mentions=discord.AllowedMentions.all(),
                )

                await interaction.response.send_message("Report has been sent!", ephemeral=True)

        await interaction.response.send_modal(Modal(member=member))

    @app_commands.command()
    @app_commands.guilds(Reference.guild)
    @checks.mod_and_above()
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

        message_logging_channel = discord.utils.get(interaction.guild.channels, id=self.message_logging_channel)

        await message_logging_channel.send(
            f"{len(deleted_messages)} messages deleted in {channel.mention}",
            file=discord.File(
                io.BytesIO("\n".join(message_log).encode()),
                filename=f"clean_content_{interaction.id}.txt",
            ),
        )

    @app_commands.command()
    @app_commands.guilds(Reference.guild)
    @app_commands.default_permissions(manage_messages=True)
    @checks.mod_and_above()
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
                raise errors.InvalidAuthorizationError("User could not be banned due to your clearance.")

            await member.send(f"You have been permanently removed from the server for following reason: \n{reason}")
        except (discord.NotFound, discord.Forbidden):
            pass

        await interaction.guild.ban(user=user, reason=reason)

        await interaction.response.send_message(
            "User has been banned", ephemeral=is_public_channel(interaction.channel)
        )

        InfractionList.new_user_infraction(
            user=user,
            kind=InfractionKind.BAN,
            level=inf_level,
            author=interaction.user,
            reason=reason,
        )

        logging_channel = discord.utils.get(interaction.guild.channels, id=self.logging_channel)

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
    @app_commands.guilds(Reference.guild)
    @app_commands.default_permissions(manage_messages=True)
    @checks.mod_and_above()
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

        await interaction.response.send_message("user was unbanned", ephemeral=is_public_channel(interaction.channel))

        logging_channel = discord.utils.get(interaction.guild.channels, id=self.logging_channel)

        embed = helper.create_embed(
            author=interaction.user,
            action="Unbanned user(s)",
            users=[user_id],
            reason=reason,
            color=discord.Color.dark_red(),
        )
        await logging_channel.send(embed=embed)

    @app_commands.command()
    @app_commands.guilds(Reference.guild)
    @app_commands.default_permissions(manage_messages=True)
    @checks.mod_and_above()
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

            raise errors.InvalidAuthorizationError("User could not be kicked due to your clearance.")

        infractions = InfractionList.from_user(member)
        if infractions.on_final:
            result = await FinalReconfirmation.handle(interaction, infractions, member, interaction.user)

            if result < 0:
                return

        await member.kick(reason=reason)

        if interaction.response.is_done():
            await interaction.edit_original_response(content="member has been kicked")
        else:
            await interaction.response.send_message(
                "member has been kicked",
                ephemeral=is_public_channel(interaction.channel),
            )

        infractions.new_infraction(
            kind=InfractionKind.KICK,
            level=inf_level,
            author=interaction.user,
            reason=reason,
        )
        infractions.update()

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

    @app_commands.command()
    @app_commands.guilds(Reference.guild)
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
            raise errors.InvalidInvocationError("Improper time provided")
        elif tot_time > 604801:
            raise errors.InvalidInvocationError("Can't mute for longer than 7 days!")
        elif tot_time < 300:
            raise errors.InvalidInvocationError("Can't mute for shorter than 5 minutes!")

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

        logging_channel = discord.utils.get(interaction.guild.channels, id=Reference.Channels.Logging.misc_actions)

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
    @app_commands.guilds(Reference.guild)
    @app_commands.default_permissions(manage_messages=True)
    @checks.mod_and_above()
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

            raise errors.InvalidAuthorizationError("user could not be muted due to your clearance")

        # time calculation
        tot_time, _ = helper.calc_time([time, ""])

        if tot_time is None:
            raise errors.InvalidInvocationError("no valid time provided")
        elif tot_time <= 0:
            raise errors.InvalidInvocationError("time can not be 0 or less")
        elif tot_time > 2419200:
            raise errors.InvalidInvocationError("time can not be longer than 28 days (2419200 seconds)")

        infractions = InfractionList.from_user(member)
        if infractions.on_final:
            result = await FinalReconfirmation.handle(interaction, infractions, member, interaction.user)

            if result < 0:
                return

        duration = datetime.timedelta(seconds=tot_time)
        finished = discord.utils.utcnow() + duration

        time_str = helper.get_time_string(tot_time)

        default_msg = "(Note: Accumulation of warns may lead to permanent removal from the server)"
        final_msg = (
            "**(This is your final warning, future infractions will lead to a non negotiable ban from the server)**"
        )
        if final:
            default_msg = final_msg

        try:
            await member.send(f"You have been muted for {time_str}.\nGiven reason: {reason}\n{default_msg}")
        except discord.Forbidden:
            pass

        await member.timeout(finished)

        if interaction.response.is_done():
            await interaction.edit_original_response(content="member has been muted")
        else:
            await interaction.response.send_message(
                "member has been muted",
                ephemeral=is_public_channel(interaction.channel),
            )

        infractions.new_infraction(
            kind=InfractionKind.MUTE,
            level=inf_level,
            author=interaction.user,
            reason=reason,
            duration=time_str,
            final=final,
        )
        infractions.update()

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

    @app_commands.command()
    @app_commands.guilds(Reference.guild)
    @app_commands.default_permissions(manage_messages=True)
    @checks.mod_and_above()
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

        logging_channel = discord.utils.get(interaction.guild.channels, id=self.logging_channel)

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
    @app_commands.guilds(Reference.guild)
    @app_commands.default_permissions(manage_messages=True)
    @checks.mod_and_above()
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

            raise errors.InvalidAuthorizationError("you do not have clearance to do that")

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

        logging_channel = discord.utils.get(interaction.guild.channels, id=self.logging_channel)

        embed = helper.create_embed(
            author=interaction.user,
            action=action,
            users=[member],
            extra=f"Role: {role.mention}",
            color=discord.Color.purple(),
        )
        await logging_channel.send(embed=embed)

    @app_commands.command()
    @app_commands.guilds(Reference.guild)
    @app_commands.default_permissions(manage_messages=True)
    @checks.mod_and_above()
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

            raise errors.InvalidAuthorizationError("user could not be warned due to your clearance")

        infractions = InfractionList.from_user(member)
        if infractions.on_final:
            result = await FinalReconfirmation.handle(interaction, infractions, member, interaction.user)

            if result < 0:
                return

        # TODO make this more modular
        default_msg = "(Note: Accumulation of warns may lead to permanent removal from the server)"
        final_msg = (
            "**(This is your final warning, future infractions will lead to a non negotiable ban from the server)**"
        )
        if final:
            default_msg = final_msg

        try:
            await member.send(f"You have been warned for {reason} {default_msg}")
        except discord.Forbidden:
            pass

        infractions.new_infraction(
            kind=InfractionKind.WARN,
            level=inf_level,
            author=interaction.user,
            reason=reason,
            final=final,
        )
        infractions.update()

        if interaction.response.is_done():
            await interaction.edit_original_response(content="user has been warned")
        else:
            await interaction.response.send_message(
                "user has been warned", ephemeral=is_public_channel(interaction.channel)
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

    @app_commands.command()
    @app_commands.guilds(Reference.guild)
    @app_commands.default_permissions(manage_messages=True)
    @checks.mod_and_above()
    async def delete_infr(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        infr_type: InfractionKind,
    ):
        """
        Allows for the deletion of an infraction
        """

        """
        Since this is a lot of code, here is a breakdown...

        IdxButton -> index button which is the button that records the input to
        select an infraction. it should only be enabled when there is a valid
        infraction for it to represent (disabled value is handled by 
        DeleteInfractionView). Its only purpose is to call a method inside the
        DeleteInfractionView passing the interaction and itself.

        DeleteInfractionView -> rather simple name. The user's infraction list
        instance is passed to the initialization along with the infraction kind
        we are attempting to delete. The infractions of that kind are split into
        chunks and each chunk is its own page of infractions show to the user of
        the command. 
        """

        class IdxButton(discord.ui.Button):
            async def callback(self, interaction: discord.Interaction):
                """
                Calls select infraction on the DeleteInfractionView to proceed
                to the confirmation phase
                """
                await self.view.select_infraction(interaction, self)

        class DeleteInfractionView(discord.ui.View):
            def __init__(self, user_infractions: InfractionList, kind: InfractionKind):
                super().__init__(timeout=60)
                """
                Splits the infractions into chunks of 5 or less and builds the
                buttons that represent the infractions posted on the page
                """

                self.user_infractions = user_infractions

                # split the infractions into chunks 5 elements or less
                infractions = user_infractions._kind_to_list(kind)
                self.chunks = [infractions[i : i + 5] for i in range(0, len(infractions), 5)]

                self.idx_buttons = []
                self.current_chunk = 0
                self.delete_infraction_idx = -1

                for i in range(0, 5):
                    disabled = i >= len(self.chunks[self.current_chunk])
                    button = IdxButton(label=str(i), disabled=disabled, row=0)
                    self.add_item(button)
                    self.idx_buttons.append(button)

            @discord.ui.button(label="<", style=discord.ButtonStyle.blurple, row=1)
            async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
                """
                Goes backwards in the pagination. Supports cycling around
                """
                new_chunk = (self.current_chunk - 1) % len(self.chunks)

                self.current_chunk = new_chunk
                await self.write_msg(interaction)

            @discord.ui.button(label=">", style=discord.ButtonStyle.blurple, row=1)
            async def forward(self, interaction: discord.Interaction, button: discord.ui.Button):
                """
                Goes forwards in the pagination. Supports cycling around
                """
                new_chunk = (self.current_chunk + 1) % len(self.chunks)

                self.current_chunk = new_chunk
                await self.write_msg(interaction)

            @discord.ui.button(label="x", style=discord.ButtonStyle.red, row=1)
            async def exit(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.message.edit(content="Exited!!!", embed=None, view=None, delete_after=5)
                self.stop()

            @discord.ui.button(label="✓", style=discord.ButtonStyle.green, row=1, disabled=True)
            async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
                if self.delete_infraction_idx == -1:
                    # This should not happen with correct logic but should
                    # provide insight on an issue if it does
                    await interaction.response.send_message("An infraction is not selected", ephemeral=True)
                    return

                success = self.user_infractions.delete_infraction(infr_type, self.delete_infraction_idx)

                if not success:
                    # This should not happen with correct logic but should
                    # provide insight on an issue if it does
                    await interaction.response.send_message("Infraction was not found", ephemeral=True)
                    return

                self.user_infractions.update()

                # TODO, log this in mod-action-logs

                await interaction.response.edit_message(
                    content="Infraction deleted successfully.", embed=None, view=None
                )
                self.stop()

            def build_embed(self) -> discord.Embed:
                """
                Builds the embed to display the current page of infractions
                """

                embed = discord.Embed(
                    title=f"{infr_type.name.title()}s for {user.name} ({user.id})",
                    color=discord.Color.magenta(),
                    timestamp=discord.utils.utcnow(),
                    description=f"Showing atmost 5 warns at a time",
                )

                embed.set_footer(text=f"Page {self.current_chunk+1}/{len(self.chunks)}")

                for i, infraction in enumerate(self.chunks[self.current_chunk]):
                    embed.add_field(
                        name=f"**Value: {i}**",
                        value=infraction.info_str(i + (5 * self.current_chunk)),
                    )

                return embed

            async def select_infraction(self, interaction: discord.Interaction, button: discord.ui.Button):
                """
                Selects the infraction that corresponds to the button passed

                This enables the phase of confirmation or declining the update.
                All index buttons are disabled and the infraction is shown to
                the user to confirm the choice.
                """

                self.delete_infraction_idx = int(button.label) + (5 * self.current_chunk)

                user_infractions = self.user_infractions

                infraction_info = user_infractions.get_infraction_info_str(infr_type, self.delete_infraction_idx)

                embed = discord.Embed(
                    title=f"Confirm deletion of {infr_type.name.lower()}:\n" + f"for {user.name} ({user.id})?",
                    color=discord.Color.magenta(),
                    timestamp=discord.utils.utcnow(),
                    description=infraction_info,
                )

                self.confirm.disabled = False
                for button in self.idx_buttons:
                    button.disabled = True

                await interaction.response.edit_message(embed=embed, view=self)

            async def write_msg(self, interaction: discord.Interaction):
                """
                Builds the embed, updates button activation and sends to discord
                """

                embed = self.build_embed()

                # update disabled buttons
                for button in self.idx_buttons:
                    button.disabled = int(button.label) >= len(self.chunks[self.current_chunk])

                await interaction.response.edit_message(embed=embed, view=self)

            async def on_timeout(self):
                """Removes the view on timeout"""

                await interaction.edit_original_response(view=None)

            async def interaction_check(self, new_interaction):
                if new_interaction.user.id == interaction.user.id:
                    return True
                else:
                    await interaction.response.send_message("You can't use that", ephemeral=True)

        user_infractions = InfractionList.from_user(user)

        if len(user_infractions._kind_to_list(infr_type)) == 0:
            await interaction.response.send_message(f"User has no {infr_type.name.lower()}s.", ephemeral=True)
            return

        div = DeleteInfractionView(user_infractions, kind=infr_type)

        embed = div.build_embed()

        await interaction.response.send_message(embed=embed, view=div, ephemeral=is_public_channel(interaction.channel))

    @app_commands.command()
    @app_commands.guilds(Reference.guild)
    @app_commands.default_permissions(manage_messages=True)
    @checks.mod_and_above()
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

            def __init__(
                self,
                user_infractions: InfractionList,
                inf_type: InfractionKind,
                label,
                **kwargs,
            ):
                super().__init__(label=label, **kwargs)
                self.inf_type = inf_type
                self.user_infractions = user_infractions

            async def callback(self, interaction):
                """
                Switches the embed to display content for the corresponding
                infraction kind
                """

                infs_embed = self.user_infractions.get_infractions_of_kind(self.inf_type)

                await interaction.response.edit_message(embed=infs_embed)

        class InfractionView(discord.ui.View):
            """
            Represents an infraction embed view. This hosts buttons of the
            different InfractionKinds to allow switching between the display of
            each infraction list.
            """

            def __init__(self, user_infractions: InfractionList):
                super().__init__(timeout=60)

                self.user_infractions = user_infractions

                for kind in InfractionKind:
                    button = InfButton(user_infractions, inf_type=kind, label=kind.name.title() + "s")
                    self.add_item(button)

            async def on_timeout(self):
                """
                Removes the view on timeout for visual aid
                """

                await interaction.edit_original_response(view=None)

        user_infractions = InfractionList.from_user(user)
        infs_embed = user_infractions.get_infractions_of_kind(InfractionKind.WARN)

        await interaction.response.send_message(
            embed=infs_embed,
            view=InfractionView(user_infractions),
            ephemeral=is_public_channel(interaction.channel),
        )

    @app_commands.command()
    @app_commands.guilds(Reference.guild)
    @app_commands.default_permissions(manage_messages=True)
    @checks.mod_and_above()
    async def detailed_infr(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        infr_type: InfractionKind,
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

        user_infractions = InfractionList.from_user(user)
        embed = user_infractions.get_detailed_infraction(infr_type, infr_id)

        if embed is None:
            await interaction.response.send_message("Infraction with given id and type not found.", ephemeral=True)

            return

        await interaction.response.send_message(embed=embed, ephemeral=is_public_channel(interaction.channel))

    @app_commands.command()
    @app_commands.guilds(Reference.guild)
    @app_commands.default_permissions(manage_messages=True)
    @checks.mod_and_above()
    async def editinfr(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        infr_type: InfractionKind,
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

        user_infractions = InfractionList.from_user(user)
        success = user_infractions.detail_infraction(infr_type, infr_id, title, description)

        if not success:
            await interaction.response.send_message("Infraction with given id and type not found.", ephemeral=True)
            return

        user_infractions.update()

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

        logging_channel = discord.utils.get(interaction.guild.channels, id=self.logging_channel)
        await logging_channel.send(embed=embed)

    @app_commands.command()
    @app_commands.guilds(Reference.guild)
    @app_commands.default_permissions(manage_messages=True)
    @checks.mod_and_above()
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

        logging_channel = discord.utils.get(interaction.guild.channels, id=self.logging_channel)

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
    @app_commands.guilds(Reference.guild)
    @app_commands.default_permissions(manage_messages=True)
    @checks.mod_and_above()
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
            return await interaction.response.send_message(f"{command_name} is not a valid command", ephemeral=True)
        if interaction.user.top_role > member.top_role:
            blacklist_member(self.bot, member, command)
            await interaction.response.send_message(f"{member.name} can no longer use {command_name}", ephemeral=True)
        else:
            await interaction.response.send_message(
                f"You cannot blacklist someone higher or equal to you smh.",
                ephemeral=True,
            )

    @app_commands.command()
    @app_commands.guilds(Reference.guild)
    @app_commands.default_permissions(manage_messages=True)
    @checks.mod_and_above()
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
            return await interaction.response.send_message(f"{command_name} is not a valid command", ephemeral=True)
        if whitelist_member(member, command):
            await interaction.response.send_message(f"{member.name} can now use {command.name}", ephemeral=True)
        else:
            await interaction.response.send_message(
                f"{member.name} is not blacklisted from {command.name}", ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(Moderation(bot))
