import gork_bot.slash_commands.testing as testing
import gork_bot.slash_commands.prompt_additions as prompt_additions

from gork_bot.bot import GorkBot


def setup_commands(bot: GorkBot) -> None:
    testing.setup(bot)
    prompt_additions.setup(bot)
