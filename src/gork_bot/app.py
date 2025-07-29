from gork_bot import DISCORD_TOKEN
from gork_bot.bot import GorkBot


def main():
    GorkBot(
        prompt_config_path="config/prompts.yaml", bot_config_path="config/bot.yaml"
    ).run(token=DISCORD_TOKEN)


def testing():
    GorkBot(
        prompt_config_path="config/prompts.yaml",
        bot_config_path="config/bot.yaml",
        testing=True,
    ).run(token=DISCORD_TOKEN)


if __name__ == "__main__":
    main()
