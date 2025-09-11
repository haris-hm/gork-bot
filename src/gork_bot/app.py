from gork_bot import DISCORD_TOKEN
from gork_bot.bot import GorkBot, setup_commands


def main():
    gork_bot: GorkBot = GorkBot(bot_config_path="config/bot.yaml")
    setup_commands(gork_bot)
    gork_bot.run(token=DISCORD_TOKEN)


def testing():
    GorkBot(
        bot_config_path="config/bot.yaml",
        testing=True,
    ).run(token=DISCORD_TOKEN)


if __name__ == "__main__":
    main()
