from discord import Interaction

from gork_bot.bot import GorkBot


def setup(bot: GorkBot) -> None:
    @bot.tree.command(name="echo", description="Echos the provided message.")
    async def __echo_command(interaction: Interaction, message: str):
        await interaction.response.send_message(message)
