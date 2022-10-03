from .helper import config_roles
from .app_errors import InvalidAuthorizationError

from discord import Interaction, app_commands


def mod_and_above():
    async def predicate(interaction: Interaction):
        user_role_ids = [x.id for x in interaction.user.roles]
        check_role_ids = [
            config_roles["mod_role"],
            config_roles["admin_role"],
            config_roles["kgsofficial_role"],
            config_roles["trainee_mod_role"],
        ]
        if not any(x in user_role_ids for x in check_role_ids):
            raise InvalidAuthorizationError
        return True

    return app_commands.check(predicate)


def devs_only():
    async def predicate(interaction: Interaction):
        if not interaction.user.id in [
            389718094270038018,  # FC
            424843380342784011,  # Oeav
            183092910495891467,  # Sloth
            248790213386567680,  # Austin
            229779964898181120,  # source
        ]:
            raise InvalidAuthorizationError
        return True

    return app_commands.check(predicate)


def general_only():
    async def predicate(interaction: Interaction):
        if (
            interaction.channel.category_id
            != 414095379156434945  # Mod channel category
            and interaction.channel_id != 414027124836532236  # general id
        ):
            raise InvalidAuthorizationError
        return True

    return app_commands.check(predicate)


def topic_perm_check():
    # check for role >= Duck(637114897544511488) and Patron
    async def predicate(interaction: Interaction):
        check_role = interaction.guild.get_role(637114897544511488)

        user = interaction.guild.get_member(interaction.user.id)
        user_role_ids = [x.id for x in user.roles]
        check_role_ids = [
            config_roles["patreon_blue_role"],
            config_roles["patreon_green_role"],
            config_roles["patreon_orange_role"],
        ]
        if interaction.user.top_role >= check_role or any(
            x in user_role_ids for x in check_role_ids
        ):
            return True
        raise InvalidAuthorizationError

    return app_commands.check(predicate)


def patreon_only():
    async def predicate(interaction: Interaction):

        user = interaction.client.get_guild(414027124836532234).get_member(
            interaction.user.id
        )
        user_role_ids = [x.id for x in user.roles]
        check_role_ids = [
            config_roles["patreon_blue_role"],
            config_roles["patreon_green_role"],
            config_roles["patreon_orange_role"],
        ]
        if not any(x in user_role_ids for x in check_role_ids):
            raise InvalidAuthorizationError
        return True

    return app_commands.check(predicate)
