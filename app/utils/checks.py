"""
Checks for the bot commands.
These checks are used to ensure that the command invoker has the necessary permissions to run the command.
"""
import discord
from discord import Interaction, app_commands
from discord.ext import commands

from .config import Reference
from .errors import InvalidAuthorizationError, InvalidInvocationError


def check(predicate):
    """
    This is a custom check decorator that works for both app_commands and
    regular text commands.
    """

    def true_decorator(decked_func):
        if isinstance(decked_func, app_commands.Command):
            app_commands.check(predicate)(decked_func)

        elif isinstance(decked_func, commands.Command):
            commands.check(predicate)(decked_func)

        else:
            app_commands.check(predicate)(decked_func)
            commands.check(predicate)(decked_func)

        return decked_func

    return true_decorator


def mod_and_above():
    """
    Checks if the command invoker has a mod role or above.
    """

    async def predicate(info: Interaction | commands.Context):
        user = info.user if isinstance(info, Interaction) else info.author
        assert isinstance(user, discord.Member)

        user_role_ids = [x.id for x in user.roles]
        check_role_ids = Reference.Roles.moderator_and_above()
        if not any(x in user_role_ids for x in check_role_ids):
            raise InvalidAuthorizationError
        return True

    return check(predicate)


def admin_and_above():
    """
    Checks if the author of the context is an administrator or kgs official.
    """

    async def predicate(info: Interaction | commands.Context):
        user = info.user if isinstance(info, Interaction) else info.author
        assert isinstance(user, discord.Member)

        user_role_ids = [x.id for x in user.roles]
        check_role_ids = Reference.Roles.admin_and_above()
        if not any(x in user_role_ids for x in check_role_ids):
            raise InvalidAuthorizationError
        return True

    return check(predicate)


def role_and_above(id: int):
    """
    Checks if the user has role above or equal to the passed role.
    """

    async def predicate(info: Interaction | commands.Context):
        user = info.user if isinstance(info, Interaction) else info.author
        guild = info.guild

        assert isinstance(user, discord.Member)
        if guild is None:
            raise InvalidInvocationError

        check_role = guild.get_role(id)  # Role could not exist if command is used in incorrect guild
        if not user.top_role >= check_role:
            raise InvalidAuthorizationError
        return True

    return check(predicate)


def mainbot_only():
    """
    Checks if the bot running the context is the main bot.
    """

    async def predicate(info: Interaction | commands.Context):
        me = info.client.user if isinstance(info, Interaction) else info.me
        assert me
        if not me.id == Reference.mainbot:
            raise InvalidInvocationError
        return True

    return check(predicate)


def devs_only():
    """
    Checks if the command invoker is in the dev list.
    """

    async def predicate(info: Interaction | commands.Context):
        user = info.user if isinstance(info, Interaction) else info.author

        if not user.id in Reference.botdevlist:
            raise InvalidAuthorizationError
        return True

    return check(predicate)


def general_only():
    """
    Checks if the command is invoked in general chat or the moderation category.
    """

    async def predicate(info: Interaction | commands.Context):
        channel = info.channel
        assert isinstance(channel, discord.TextChannel)

        if channel.category_id != Reference.Categories.moderation and channel.id != Reference.Channels.general:
            raise InvalidInvocationError(content=f"This command can only be ran in <#{Reference.Channels.general}>")
        return True

    return check(predicate)


def bot_commands_only():
    """
    Checks if the command is invoked in bot_commands or the moderation category.
    """

    async def predicate(info: Interaction | commands.Context):
        channel = info.channel

        assert isinstance(channel, discord.TextChannel)
        if channel.category_id != Reference.Categories.moderation and channel.id != Reference.Channels.bot_commands:
            raise InvalidInvocationError(
                content=f"This command can only be ran in <#{Reference.Channels.bot_commands}>"
            )
        return True

    return check(predicate)


def topic_perm_check():
    """
    Checks if the command invoker has the duck role+ or a patreon role.
    """

    async def predicate(info: Interaction | commands.Context):
        user = info.user if isinstance(info, Interaction) else info.author
        guild = info.guild

        assert isinstance(user, discord.Member)

        if guild is None:
            raise InvalidInvocationError

        check_role = guild.get_role(Reference.Roles.duck)

        user_role_ids = [x.id for x in user.roles]
        check_role_ids = Reference.Roles.patreon()
        if user.top_role >= check_role or any(x in user_role_ids for x in check_role_ids):
            return True
        raise InvalidAuthorizationError(content="This can only be ran by ducks+ and patreon members")

    return check(predicate)


def patreon_only():
    """
    Checks if the command invoker has the duck role+ or a patreon role.
    """

    async def predicate(info: Interaction | commands.Context):
        client = info.client if isinstance(info, Interaction) else info.bot
        user = info.user if isinstance(info, Interaction) else info.author

        member = client.get_guild(Reference.guild).get_member(user.id)  # type: ignore
        assert member
        member_role_ids = [x.id for x in member.roles]
        check_role_ids = Reference.Roles.patreon()
        if not any(x in member_role_ids for x in check_role_ids):
            raise InvalidAuthorizationError
        return True

    return check(predicate)
