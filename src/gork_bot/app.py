import dotenv
import os

from gork_bot.bot import GorkBot
from openai import OpenAI

# Load environment variables from .env file
dotenv.load_dotenv()
DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN")


def main():
    GorkBot().run(token=DISCORD_TOKEN)
