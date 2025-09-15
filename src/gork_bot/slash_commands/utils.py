from discord import Interaction, Member, User
from discord.app_commands import check


def user_has_permission(*required_permissions: tuple[str]) -> check:
    async def predicate(interaction: Interaction) -> bool:
        user: User | Member = interaction.user
        if not isinstance(user, (Member, User)):
            return False

        for perm in required_permissions:
            if not getattr(user.guild_permissions, perm, False):
                return False
        return True

    return check(predicate)
