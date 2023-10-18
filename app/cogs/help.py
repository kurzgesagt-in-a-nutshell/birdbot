import asyncio
import logging
import re

import discord
from discord import Interaction, app_commands
from discord import ui as dui
from discord.ext import commands, tasks

from app.birdbot import BirdBot
from app.utils import checks
from app.utils.config import Reference
from app.utils.helper import get_active_staff

logger = logging.getLogger(__name__)


class ReportView(dui.View):
    """
    Handles the interactions with the buttons below a report embed as well as
    the continual pestering of active reports.
    """

    def __init__(self, *, bot: BirdBot, resolve_id: str, claim_id: str):
        super().__init__(timeout=None)

        self.bot = bot

        self._resolve.custom_id = resolve_id
        self._claim.custom_id = claim_id

        self.active_reports: list[int] = []

        self.resolve_lock = asyncio.Lock()

        self._reminder_task.start()

    def insert_issue(self, message: discord.Message):
        """
        Inserts a new issue into the active issues
        """

        self.active_reports.append(message.id)

    def collect_claimed(self, embed: discord.Embed) -> list[int]:
        """
        Collects a list of users who have claimed the issue
        """

        footer = embed.footer.text
        if footer is None:
            return []

        matches = re.findall(r"([\d]+)", footer)

        return [int(i) for i in matches]

    async def get_report_author(self, embed: discord.Embed) -> discord.User:
        """
        Strips the user id out of the author text for use
        """

        author_text = embed.author.name
        if author_text is None or (match := re.search(r"\([\d]+\)", author_text)) is None:

            raise Exception("Report author does not appear to be defined")

        user_id = int(match.group(0).strip("()"))

        return await self.bot.fetch_user(user_id)

    @dui.button(label="Mark as resolved")
    async def _resolve(self, interaction: Interaction, button: dui.Button):
        """
        Marks the embed as resolved and removes the report from the ping cycle.

        DMs the reporter that the report has been marked as resolved.
        """
        await interaction.response.defer(ephemeral=True)

        async with self.resolve_lock:
            if (message := interaction.message) is None or (embed := message.embeds[0]) is None:
                return

            if message.id not in self.active_reports:
                await interaction.followup.send("This issue has already been marked as resolved", ephemeral=True)
                return

            user = interaction.user

            # Update the embed

            embed.color = 0x00FF00
            embed.set_footer(text=f"Marked resolved by {user.name}({user.id})", icon_url=user.display_avatar.url)

            self.active_reports.remove(message.id)
            await interaction.followup.edit_message(message.id, embed=embed, view=None)

        # finally once we are out of the lock, DM the user who reported
        report_author = await self.get_report_author(embed)
        try:
            await report_author.send(
                "Your report has been marked as resolved \n"
                + "If you think this is not the case, please submit a new report"
                + " with more detailed information. \n\n"
                + "# Your report details \n"
                + f"{embed.description}"
            )
        except discord.Forbidden:
            pass

    @dui.button(label="Claim this issue")
    async def _claim(self, interaction: Interaction, button: dui.Button):
        """
        Adds the user to the active actors of the report. If one user has
        selected this then this is prioritized over active moderators.

        This also makes it remind the moderator who has claimed the report every
        15 minutes rather than every 5
        """

        if (message := interaction.message) is None or (embed := message.embeds[0]) is None:
            return

        claimed = self.collect_claimed(embed)

        if interaction.user.id in claimed:
            await interaction.response.send_message("You have already claimed this issue", ephemeral=True)
            return

        claimed.append(interaction.user.id)

        embed.set_footer(text=f"Claimed: ({str(claimed).strip('[]')})")

        await interaction.response.edit_message(embed=embed)

    def stop(self):
        """
        Stops the view and the task
        """

        super().stop()

        self._reminder_task.stop()

    @tasks.loop(minutes=5)
    async def _reminder_task(self):
        """
        Checks periodically for reports that have not been dealt with.

        Reports that are unclaimed are reminded about each iteration.
        Reports that are claimed and unresolved are reminded about each 3
        iterations
        """
        unresolved: list[discord.Message] = []
        in_progress: list[discord.Message] = []

        logger.debug("Report Reminder task begins")
        logger.debug(self._reminder_task.current_loop)

        mod_channel = self.bot.get_channel(Reference.Channels.mod_chat)
        if not isinstance(mod_channel, discord.TextChannel):
            raise Exception("Mod chat is appearing as a non text channel")

        for report in self.active_reports:
            try:
                message = await mod_channel.fetch_message(report)
                embed = message.embeds[0]

                claimed = self.collect_claimed(embed)
                to_add = in_progress if len(claimed) > 0 else unresolved

                to_add.append(message)
            except discord.NotFound:
                # Removes the reference if the message is not found

                self.active_reports.remove(report)

        if len(unresolved) == 0 and len(in_progress) == 0:
            logger.debug("Report Reminder no active reports to remind")
            return

        content = ", ".join([m.jump_url for m in unresolved]) + "\n" + ", ".join([m.jump_url for m in in_progress])

        await mod_channel.send(content)

    @_reminder_task.before_loop
    async def _before_reminder(self):
        """
        This needs to be done only to satisfy requirements for the first loop
        and for following loops when the bot may not be actively connected to
        discord
        """

        await self.bot.wait_until_ready()


class ReportModal(dui.Modal):
    text = dui.TextInput(
        label="Please describe your issue:",
        style=discord.TextStyle.long,
    )
    message = dui.TextInput(
        label="Helpful discord link if any:",
        style=discord.TextStyle.short,
        placeholder="https://discord.com/channels/414027124836532234/414268041787080708/937750299165208607",
        required=False,
    )

    def __init__(self, member, report_view: ReportView):
        super().__init__(title="Report")
        self.member = member
        self.report_view = report_view

    def build_embed(self, interaction: Interaction, channel_mention: str, message_link: str) -> discord.Embed:
        description = self.text.value

        mod_embed = discord.Embed(
            title="NEW REPORT",
            color=0xFF9000,
            description=f"**Content:** {description} \n"
            + f"**User Involved:** {self.member} \n"
            + f"**Channel Location:** {channel_mention} | **Link:** {message_link}",
        )
        mod_embed.set_author(
            name=f"{interaction.user.name} ({interaction.user.id})",
            icon_url=interaction.user.display_avatar.url,
        )

        return mod_embed

    async def on_submit(self, interaction: discord.Interaction):
        """
        Validates the user input where needed and provides a report embed in the
        moderation chat.
        """

        message_link = self.message.value

        channel = interaction.channel
        if isinstance(channel, (discord.abc.GuildChannel, discord.Thread)):
            channel_mention = channel.mention

            # This allows you to jump to the history in chat when the report was
            # made
            if message_link is None or message_link == "":
                message_link = f"https://discord.com/channels/414027124836532234/{channel.id}/{interaction.id}"

        else:
            channel_mention = "Sent through DMs"

        mod_channel = interaction.client.get_channel(Reference.Channels.mod_chat)
        if not isinstance(mod_channel, discord.TextChannel):
            raise Exception("The destination of the report does not exist")

        report_message = await mod_channel.send(
            get_active_staff(interaction.client),
            embed=self.build_embed(interaction, channel_mention, message_link),
            view=self.report_view,
            allowed_mentions=discord.AllowedMentions.none(),
        )

        self.report_view.insert_issue(report_message)

        await interaction.response.send_message("Your report has been sent!", ephemeral=True)


class Help(commands.Cog):
    def __init__(self, bot: BirdBot):
        self.logger = logging.getLogger("Help")
        self.bot = bot
        self.bot.remove_command("help")

    async def cog_load(self):
        """
        Creates the ReportView class Object and begins listening to new events
        """

        buser = self.bot._user()

        self.REPORT_VIEW = ReportView(
            bot=self.bot,
            resolve_id=f"REPORT-RESOLVE-{buser.id}",
            claim_id=f"REPORT-CLAIM-{buser.id}",
        )

        self.bot.add_view(self.REPORT_VIEW)

    async def cog_unload(self) -> None:
        """
        Stops both the ReportView listening and task loop within the ReportView
        """

        self.REPORT_VIEW.stop()

    # TODO: Convert the output to embed or some UI
    # TODO: Remove mod_and_above and default_permission check.
    @app_commands.command()
    @checks.mod_and_above()
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.checks.cooldown(
        1,
        10,
    )
    async def help(self, interaction: discord.Interaction):
        """
        Display help (Incomplete command)
        """

        await interaction.response.defer(ephemeral=True)

        command_tree_global = self.bot.tree.get_commands()
        command_tree_guild = self.bot.tree.get_commands(guild=interaction.guild)

        cmds = []

        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild
        for cmd in command_tree_global:
            if isinstance(cmd, discord.app_commands.commands.Command):
                cmds.append(cmd.name)

            elif isinstance(cmd, discord.app_commands.commands.Group):
                for c in cmd.commands:
                    cmds.append(f"{cmd.name} {c.name}")

        for cmd in command_tree_guild:
            if isinstance(cmd, discord.app_commands.commands.Command):
                if cmd.default_permissions and cmd.default_permissions.manage_messages:
                    if interaction.user.top_role >= interaction.guild.get_role(Reference.Roles.moderator):
                        cmds.append(cmd.name)
                    else:
                        continue
                else:
                    cmds.append(cmd.name)

            elif isinstance(cmd, discord.app_commands.commands.Group):
                for c in cmd.commands:
                    if cmd.default_permissions:
                        if cmd.default_permissions.manage_messages:
                            if interaction.user.top_role >= interaction.guild.get_role(Reference.Roles.moderator):
                                cmds.append(f"{cmd.name} {c.name}")
                            else:
                                continue
                        else:
                            cmds.append(f"{cmd.name} {c.name}")

                    elif c.default_permissions:
                        if c.default_permissions.manage_messages:
                            if interaction.user.top_role >= interaction.guild.get_role(Reference.Roles.moderator):
                                cmds.append(f"{cmd.name} {c.name}")
                            else:
                                continue
                        else:
                            cmds.append(f"{cmd.name} {c.name}")

        await interaction.edit_original_response(content=f"Commands: {' '.join(cmds)}")

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.checks.cooldown(
        1,
        10,
    )
    async def ping(self, interaction: discord.Interaction):
        """
        Ping Pong 🏓
        """
        await interaction.response.send_message(f"{int(self.bot.latency * 1000)} ms")

    @app_commands.command()
    @app_commands.checks.cooldown(1, 30)
    async def report(
        self,
        interaction: discord.Interaction,
        member: discord.Member | discord.User | None,
    ):
        """Report issues to the moderation team, gives you an UI

        Parameters
        ----------
        member: discord.Member
            Mention or ID of member to report (is optional)
        """

        await interaction.response.send_modal(ReportModal(member=member, report_view=self.REPORT_VIEW))


async def setup(bot: BirdBot):
    await bot.add_cog(Help(bot))
