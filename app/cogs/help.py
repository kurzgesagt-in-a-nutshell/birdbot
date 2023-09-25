import logging

import discord
from discord import app_commands
from discord.ext import commands

from app.utils import checks
from app.utils.config import Reference
from app.birdbot import BirdBot


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


async def setup(bot: BirdBot):
    await bot.add_cog(Help(bot))
