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
