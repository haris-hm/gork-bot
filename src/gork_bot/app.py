import dotenv
import os

from gork_bot.bot import GorkBot

dotenv.load_dotenv()
DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN")


def main():
    GorkBot(
        prompt_config_path="config/prompts.json", bot_config_path="config/bot.json"
    ).run(token=DISCORD_TOKEN)

if __name__ == "__main__":
    main()
