from gork_bot.bot import GorkBot
import dotenv
import os

# Load environment variables from .env file
dotenv.load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")


def main():
    GorkBot().run(token=DISCORD_TOKEN)
