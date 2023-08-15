import traceback, io

from discord import (app_commands, Interaction)
import discord

from utils import app_errors
from utils.config import Reference

# TODO Move to separate file once util is organized
# currently would throw a circular import error
async def maybe_responded(interaction: Interaction, *args, **kwargs):
    """
    Either responds or sends a followup on an interaction response
    """
    if interaction.response.is_done():
        await interaction.followup.send(*args, **kwargs)

        return

    await interaction.response.send_message(*args, **kwargs)


class BirdTree(app_commands.CommandTree):
    """
    Subclass of app_commands.CommandTree to define the behavior for the birdbot
    tree.

    Handles thrown errors within the tree and interactions between all commands
    """

    async def alert(self, interaction: Interaction, error: Exception):
        """
        Attempts to altert the discord channel logs of an exception
        """

        channel = await interaction.client.fetch_channel(Reference.Channels.Logging.dev)

        content = traceback.format_exc()

        file = discord.File(
            io.BytesIO(bytes(content, encoding="UTF-8")), filename=f"{type(error)}.py"
        )

        embed = discord.Embed(
            title="Unhandled Exception Alert",
            description=f"```\nContext: \nguild:{repr(interaction.guild)}\n{repr(interaction.channel)}\n{repr(interaction.user)}\n```",  # f"```py\n{content[2000:].strip()}\n```"
        )

        await channel.send(embed=embed, file=file)

    async def on_error(
        self, interaction: Interaction, error: app_commands.AppCommandError
    ):
        """Handles errors thrown within the command tree"""
        if isinstance(error, app_commands.CheckFailure):
            # Inform user of failure ephemerally

            if isinstance(error, app_errors.InvalidAuthorizationError):

                msg = f"<:kgsNo:955703108565098496> {str(error)}"
                await maybe_responded(interaction, msg, ephemeral=True)

                return

        elif isinstance(error, app_errors.InvalidInvocationError):
            # inform user of invalid interaction input ephemerally

            msg = f"<:kgsNo:955703108565098496> {str(error)}"
            await maybe_responded(interaction, msg, ephemeral=True)

            return

        if isinstance(error, app_commands.errors.CommandOnCooldown):
            msg = f"<:kgsNo:955703108565098496> {str(error)}"
            await maybe_responded(interaction, msg, ephemeral=True)

            return
        # most cases this will consist of errors thrown by the actual code
        # TODO send in <#865321589919055882>

        msg = f"an internal error occurred. if this continues please inform an active bot dev"
        await maybe_responded(
            interaction,
            msg,
            ephemeral=interaction.channel.category_id
            != Reference.Categories.moderation
        )

        try:
            await self.alert(interaction, error)
        except Exception as e:
            await super().on_error(interaction, e)