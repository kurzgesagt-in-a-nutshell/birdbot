import traceback, io

from discord import (app_commands, Interaction)
import discord

from .utils import errors
from .utils.config import Reference

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
        if isinstance(error, errors.InternalError):
            # Inform user of failure ephemerally


            embed = error.format_notif_embed(interaction)
            await maybe_responded(interaction, embed=embed, ephemeral=True)

            return
        elif isinstance(error, app_commands.CheckFailure):

            user_shown_error = errors.CheckFailure(
                content=str(error)
            )

            embed = user_shown_error.format_notif_embed(interaction)
            await maybe_responded(interaction, embed=embed, ephemeral=True)

            return

        # most cases this will consist of errors thrown by the actual code

        is_in_public_channel = (
            interaction.channel.category_id!= Reference.Categories.moderation
        )

        user_shown_error = errors.InternalError()
        await maybe_responded(
            interaction,
            embed = user_shown_error.format_notif_embed(interaction),
            ephemeral=is_in_public_channel
        )

        try:
            await self.alert(interaction, error)
        except Exception as e:
            await super().on_error(interaction, e)