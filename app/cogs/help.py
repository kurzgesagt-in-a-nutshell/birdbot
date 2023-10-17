import logging

import discord
from discord import Interaction, app_commands, ui as dui
from discord.ext import commands

from discord.ext import tasks

from app.birdbot import BirdBot
from app.utils import checks
from app.utils.config import Reference
from app.utils.helper import get_active_staff

class ReportView(dui.View):
    """
    Handles the interactions with the buttons below a report embed as well as
    the continual pestering of active reports.
    """

    def __init__(self, *, resolve_id:str, claim_id:str):
        super().__init__(timeout=None)

        self._resolve.custom_id = resolve_id
        self._claim.custom_id = claim_id

        self.active_reports = []

    async def insert_issue(self):
        """
        Inserts a new issue into the active issues
        """
        
        pass
    
    @dui.button(label="Mark as resolved")
    async def _resolve(self, interaction: Interaction, button: dui.Button):
        """
        Marks the embed as resolved and removes the report from the ping cycle.
        """
        
        pass

    @dui.button(label="Claim this issue")
    async def _claim(self, interaction: Interaction, button: dui.Button):
        """
        Adds the user to the active actors of the report. If one user has
        selected this then this is prioritized over active moderators.

        This also makes it remind the moderator who has claimed the report every
        15 minutes rather than every 5
        """

    @tasks.loop()
    async def _reminder_task(self,):
        """
        Checks periodically for reports that have not been dealt with.
        """
        
        for report in self.active_reports:
            pass

class ReportModal(dui.Modal):
    text = dui.TextInput(
        label="Please describe your issue:",
        style=discord.TextStyle.long,
    )
    message = dui.TextInput(
        label="Provide a link to a relevant message if helpful:",
        style=discord.TextStyle.short,
        placeholder="https://discord.com/channels/414027124836532234/414268041787080708/937750299165208607",
        required=False,
    )

    def __init__(self, member):
        super().__init__(title="Report")
        self.member = member

    def build_embed(
            self, 
            interaction: Interaction, 
            channel_mention: str, 
            message_link: str
        ) -> discord.Embed:
        description = self.text.value
        
        mod_embed = discord.Embed(
            title="NEW REPORT",
            color=0xFF9000,
            description=f"\
            **Content:** {description} \n\
            **User Involved:** {self.member} \n\
            **Channel Location:** {channel_mention} | **Link:** {message_link}\
            ",
        )
        mod_embed.set_author(
            name=f"{interaction.user.name} ({interaction.user.id})",
            icon_url=interaction.user.display_avatar.url,
        )

        return mod_embed

    async def on_submit(self, interaction: discord.Interaction):
        """
        Validates the user input where needed and provides a report embed in the
        moderation chat
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

        await mod_channel.send(
            get_active_staff(interaction.client),
            embed=self.build_embed(interaction, channel_mention, message_link),
            allowed_mentions=discord.AllowedMentions.all(),
        )

        await interaction.response.send_message("Your report has been sent!", ephemeral=True)

class Help(commands.Cog):
    def __init__(self, bot: BirdBot):
        self.logger = logging.getLogger("Help")
        self.bot = bot
        self.bot.remove_command("help")

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info("loaded Help")

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
        mod_channel = self.bot._get_channel(Reference.Channels.mod_chat)

        await interaction.response.send_modal(ReportModal(member=member))


async def setup(bot: BirdBot):
    await bot.add_cog(Help(bot))
