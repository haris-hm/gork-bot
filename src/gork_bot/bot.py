import re
from discord import Intents, Message, Client


class GorkBot(Client):
    def __init__(self):
        intents = Intents.default()
        intents.guild_messages = True
        intents.message_content = True
        intents.messages = True
        intents.guilds = True
        super().__init__(intents=intents)

    async def on_message(self, message: Message):
        if message.author == self.user:
            return

        if message.content.startswith("$hello"):
            await message.channel.send("Hello World!")

        print(f"Message interaction: {message.reference}, ")

    def message_contains_image():
        return

    def parse_message(self, message: Message):
        message.interaction
        return
