from .config import Reference
from .app_errors import InvalidAuthorizationError

from discord import Interaction, app_commands


def mod_and_above():
    async def predicate(interaction: Interaction):
        user_role_ids = [x.id for x in interaction.user.roles]
        check_role_ids = Reference.Roles.moderator_and_above()
        if not any(x in user_role_ids for x in check_role_ids):
            raise InvalidAuthorizationError
        return True

    return app_commands.check(predicate)


def devs_only():
    async def predicate(interaction: Interaction):
        if not interaction.user.id in Reference.botdevlist:
            raise InvalidAuthorizationError
        return True

    return app_commands.check(predicate)


def general_only():
    async def predicate(interaction: Interaction):
        if (
            interaction.channel.category_id != Reference.Categories.moderation
            and interaction.channel_id != Reference.Channels.general
        ):
            raise InvalidAuthorizationError
        return True

    return app_commands.check(predicate)


def bot_commands_only():
    async def predicate(interaction: Interaction):
        if (
            interaction.channel.category_id != Reference.Categories.moderation
            and interaction.channel_id != Reference.Channels.bot_commands
        ):
            raise InvalidAuthorizationError
        return True

    return app_commands.check(predicate)


def topic_perm_check():
    async def predicate(interaction: Interaction):
        check_role = interaction.guild.get_role(Reference.Roles.duck)

        user = interaction.guild.get_member(interaction.user.id)
        user_role_ids = [x.id for x in user.roles]
        check_role_ids = Reference.Roles.patreon()
        if interaction.user.top_role >= check_role or any(
            x in user_role_ids for x in check_role_ids
        ):
            return True
        raise InvalidAuthorizationError

    return app_commands.check(predicate)


def patreon_only():
    async def predicate(interaction: Interaction):

        user = interaction.client.get_guild(Reference.guild).get_member(
            interaction.user.id
        )
        user_role_ids = [x.id for x in user.roles]
        check_role_ids = Reference.Roles.patreon()
        if not any(x in user_role_ids for x in check_role_ids):
            raise InvalidAuthorizationError
        return True

    return app_commands.check(predicate)
