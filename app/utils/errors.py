"""
Contains all internal errors for the program.

Behavior for errors are within the InternalError class and alternations are made in inherited classes. 
"""

from discord import Embed, Interaction, app_commands
from discord.ext import commands

from .config import Reference


class InternalError(Exception):
    """
    Base class for all internal errors.
    """

    title = "Internal Error"
    content = "an unhandled internal error occurred. if this continues please inform an active bot dev"
    color = 0xC6612A

    def __init__(self, *, content: str | None = None):
        if content is not None:
            self.content = content

    def format_notif_embed(self, info: commands.Context | Interaction):
        # interaction = info if isinstance(info, Interaction) else None
        # context = info if isinstance(info, commands.Context) else None

        embed = Embed(title=self.title, color=self.color, description=self.content.format(info=info))

        return embed


class CheckFailure(InternalError, app_commands.CheckFailure, commands.CheckFailure):
    """
    InternalError and CheckFailure for both slash and message commands.
    """

    title = f"{Reference.Emoji.PartialString.kgsNo} You can not use this command"
    content = "Default, Bot Devs need to provide better info here"


class InvalidAuthorizationError(CheckFailure):
    """
    Raised when user does not have access to run a command.
    """

    title = f"{Reference.Emoji.PartialString.kgsNo} Invalid Authorization"
    content = "```\nYou do not have access to run this command\n```"


class InvalidInvocationError(CheckFailure):
    """
    Raised when user runs a command in the wrong place.
    """

    title = f"{Reference.Emoji.PartialString.kgsNo} Invalid Invocation"
    content = "```\nThis command was ran in an invalid context\n```"


class InvalidParameterError(CheckFailure):
    """
    Raised when the user provides bad parameters for the command.
    """

    title = f"{Reference.Emoji.PartialString.kgsNo} Invalid Parameters"
    content = "The parameters you provided are not accepted in this context"


class InvalidFunctionUsage(InternalError):
    """
    Usually raised when self.bot custom functions are used incorrectly.
    """

    pass
