# Copyright (C) 2024, Kurzgesagt Community Devs
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

"""
This cog defines the ColorSelect class, which is responsible for handling the removal and addition of exclusive colored roles when a member no longer has the role that proves the color.
It also allows users to add or remove a colored role based on their current roles.
"""
import logging
from typing import List, Literal

import discord
from discord import Interaction, app_commands
from discord.app_commands.models import Choice
from discord.ext import commands

from app.birdbot import BirdBot
from app.utils import errors
from app.utils.config import ExclusiveColors, Reference

logger = logging.getLogger(__name__)


class ExclusiveColorTransformer(app_commands.Transformer):
    @staticmethod
    def selectable_roles(member: discord.Member) -> List[discord.Role]:
        """
        Returns a list of selectable roles from the member's found roles.
        """

        # iterate through all of the exclusive colors
        # if the member has an unlocker for an exclusive role, add it to the
        # result list to be returned
        result = []

        for role in member.roles:

            for _, value in ExclusiveColors.exclusive_colors.items():
                if role.id in value["unlockers"]:
                    result.append(member.guild.get_role(value["id"]))

        return result

    async def transform(self, interaction: Interaction, value: str) -> discord.Role:
        """
        Transforms the string value into an exclusive colored role.
        """

        if not isinstance(interaction.user, discord.Member):
            raise errors.InvalidInvocationError(content="This command must be ran in a server")

        roles = ExclusiveColorTransformer.selectable_roles(interaction.user)

        for role in roles:
            if role.name == value:
                return role

        raise errors.InvalidParameterError(
            content="The role to add could not be resolved or you do not have\
                permission to apply it."
        )

    async def autocomplete(self, interaction: Interaction, value: str) -> List[Choice[str]]:
        """
        Returns a list of chocies (exclusive colored roles) for the member to pick from.

        This method only returns roles that they have access to.
        """

        if not isinstance(interaction.user, discord.Member):
            return []

        roles = ExclusiveColorTransformer.selectable_roles(interaction.user)

        return [Choice(name=r.name, value=r.name) for r in roles]


class ColorSelect(commands.Cog):
    """
    Handles the removal of exclusive colored roles when a member no longer has the role that proves the color.

    Allows users to add or remove a colored role based on their current roles.
    """

    def __init__(self, bot: BirdBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """
        Checks if the provided members roles are different.

        If so, check if the exclusive colored roles applied, if any, are valid.
        """

        if before.roles == after.roles:
            return

        # check if selectable roles list is less than 'before'. if so then check
        # for possible exclusive roles to remove.

        roleids = [r.id for r in after.roles]

        for name, value in ExclusiveColors.exclusive_colors.items():
            has_unlocker_role = False

            for roleid in roleids:
                if roleid in value["unlockers"]:
                    has_unlocker_role = True
                    break

            if value["id"] in roleids and not has_unlocker_role:
                logger.info(
                    f"removing : {value['id']} from user who does not \
                    have access to it anymore"
                )

                await after.remove_roles(discord.Object(value["id"]), reason="auto remove color")

    @app_commands.command(name="color", description="Provides exclusive name colors")
    async def color(
        self,
        interaction: Interaction,
        action: Literal["add", "remove"],
        color: app_commands.Transform[discord.Role, ExclusiveColorTransformer],
    ):
        """
        Allows the member to select a role to apply to themselves based on the colored configuration.

        They can select to add or remove the role and only roles they have access to apply are provided in autocomplete.
        """

        if (
            not isinstance(interaction.user, discord.Member)
            or interaction.guild is None
            or interaction.guild.id != Reference.guild
        ):

            raise errors.InvalidInvocationError(content="This command must be ran in the kurzgesagt guild")

        if action == "add":
            await interaction.user.add_roles(color, reason="color role update")
            logger.debug("added role")
        elif action == "remove":
            await interaction.user.remove_roles(color, reason="color role update")
            logger.debug("removed role")

        await interaction.response.send_message(content=f"{action.title().strip('e')}ed {color.name}", ephemeral=True)


async def setup(bot: BirdBot):
    await bot.add_cog(ColorSelect(bot))
