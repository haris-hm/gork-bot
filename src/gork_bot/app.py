from gork_bot.bot import GorkBot
from openai import OpenAI
import dotenv
import os

# Load environment variables from .env file
dotenv.load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_KEY")


def main():
    client = OpenAI(api_key=OPENAI_API_KEY)
    GorkBot(openai_client=client).run(token=DISCORD_TOKEN)
