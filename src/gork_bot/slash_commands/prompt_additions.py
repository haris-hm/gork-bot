from discord import Guild, Interaction, Member, User
from discord.app_commands import Group as AppCommandGroup
from discord.app_commands import autocomplete, Choice
from pymysql import Connection

from gork_bot.bot import GorkBot

from gork_bot.db_service.models import GorkGuild, GorkMessageContext
from gork_bot.db_service.connection import db_connect

prompt_addition_group: AppCommandGroup = AppCommandGroup(
    name="prompt_additions", description="Manage prompt additions."
)


async def remove_autocomplete(
    interaction: Interaction,
    current: str,
) -> list[Choice[str]]:
    guild: Guild = interaction.guild
    if guild is None:
        return []
    connection: Connection = db_connect()
    try:
        message_context: GorkMessageContext = GorkMessageContext(
            user_id=interaction.user.id, guild_id=guild.id, connection=connection
        )
        gork_guild: GorkGuild = message_context.guild
        prompt_additions: list[str] = gork_guild.get_all_prompt_additions()
    finally:
        connection.close()
    # Filter suggestions based on what the user has typed so far
    return [
        Choice(name=addition[:100], value=addition[:100])
        for addition in prompt_additions
        if current.lower() in addition.lower()
    ]


@prompt_addition_group.command(
    name="add",
    description="Adds a new prompt addition into the guild's prompt addition list.",
)
async def __add(interaction: Interaction, prompt_addition: str):
    guild: Guild = interaction.guild
    user: User | Member = interaction.user

    if guild is None:
        await interaction.response.send_message(
            "This command can only be used in a guild.", ephemeral=True
        )
        return

    connection: Connection = db_connect()

    try:
        message_context: GorkMessageContext = GorkMessageContext(
            user_id=user.id, guild_id=guild.id, connection=connection
        )
        gork_guild: GorkGuild = message_context.guild

        if not gork_guild.channel_allowed(channel_id=interaction.channel_id):
            await interaction.response.send_message(
                "This channel is not allowed to use bot commands.", ephemeral=True
            )
            return

        gork_guild.add_prompt_addition(addition_text=prompt_addition)
    finally:
        connection.close()

    await interaction.response.send_message(
        f'"{prompt_addition}" has been added to the guild\'s prompt addition list.',
        ephemeral=True,
    )


@prompt_addition_group.command(
    name="remove",
    description="Removes a prompt addition from the guild's prompt addition list.",
)
@autocomplete(prompt_addition=remove_autocomplete)
async def __remove(interaction: Interaction, prompt_addition: str):
    guild: Guild = interaction.guild
    user: User | Member = interaction.user

    if guild is None:
        await interaction.response.send_message(
            "This command can only be used in a guild.", ephemeral=True
        )
        return

    connection: Connection = db_connect()

    try:
        message_context: GorkMessageContext = GorkMessageContext(
            user_id=user.id, guild_id=guild.id, connection=connection
        )
        gork_guild: GorkGuild = message_context.guild

        if not gork_guild.channel_allowed(channel_id=interaction.channel_id):
            await interaction.response.send_message(
                "This channel is not allowed to use bot commands.", ephemeral=True
            )
            return

        removed: bool = gork_guild.remove_prompt_addition(addition_text=prompt_addition)
    finally:
        connection.close()

    if removed:
        await interaction.response.send_message(
            f'"{prompt_addition}" has been removed from the guild\'s prompt addition list.',
            ephemeral=True,
        )
    else:
        await interaction.response.send_message(
            f'"{prompt_addition}" was not found in the guild\'s prompt addition list.',
            ephemeral=True,
        )


@prompt_addition_group.command(
    name="list",
    description="Lists the current guild's prompt additions.",
)
async def __list(interaction: Interaction):
    guild: Guild = interaction.guild

    if guild is None:
        await interaction.response.send_message(
            "This command can only be used in a guild.", ephemeral=True
        )
        return

    connection: Connection = db_connect()

    try:
        message_context: GorkMessageContext = GorkMessageContext(
            user_id=interaction.user.id, guild_id=guild.id, connection=connection
        )
        gork_guild: GorkGuild = message_context.guild

        if not gork_guild.channel_allowed(channel_id=interaction.channel_id):
            await interaction.response.send_message(
                "This channel is not allowed to use bot commands.", ephemeral=True
            )
            return

        prompt_additions: list[str] = gork_guild.get_all_prompt_additions()
    finally:
        connection.close()

    if not prompt_additions:
        await interaction.response.send_message(
            "There are currently no prompt additions for this guild.",
            ephemeral=True,
        )
        return

    additions_list: str = "\n".join(
        [f"{idx + 1}. {addition}" for idx, addition in enumerate(prompt_additions)]
    )
    addition_chance: float = 1 / len(prompt_additions)

    response_message: str = (
        "Current prompt additions for this guild:\n"
        f"{additions_list}\n\n"
        f"Chance of a certain addition being used is: {addition_chance:.2%}"
    )

    await interaction.response.send_message(
        response_message,
        ephemeral=True,
    )


def setup(bot: GorkBot) -> None:
    bot.tree.add_command(prompt_addition_group)
