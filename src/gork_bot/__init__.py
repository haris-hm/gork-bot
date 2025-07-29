import dotenv
import os

from openai import OpenAI

dotenv.load_dotenv()

DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY: str = os.getenv("OPENAI_KEY")
CLIENT_KEY: str = os.getenv("CLIENT_KEY", "gork_bot")

OAI_CLIENT: OpenAI = OpenAI(api_key=OPENAI_API_KEY)
