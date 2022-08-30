
from discord import app_commands

class InvalidInvocationError(app_commands.AppCommandError):

    """
    Called when a combination of arguments used within a command are invalid or
    the state of the execution is not valid.
    """

class InvalidAuthorizationError(app_commands.CheckFailure):

    """
    Base class to be thrown when invalid authorization is provided.
    """