import re
from discord import Intents, Message, Client, Attachment, MessageReference
from typing import Any
from gork_bot.ai_requests import InputBuilder, PromptBuilder, Models
from openai import OpenAI


class GorkBot(Client):
    def __init__(self, openai_client: OpenAI):
        intents = Intents.default()
        intents.guild_messages = True
        intents.message_content = True
        intents.messages = True
        intents.guilds = True
        self.openai_client = openai_client
        super().__init__(intents=intents)

    async def on_message(self, message: Message):
        if message.author == self.user or self.user not in message.mentions:
            return

        print(f"Received Message: {message.content} from {message.author.name}")

        parsed_message: dict[str, str] | None = await self.parse_message(message)

        if not parsed_message:
            return

        input_text: str = parsed_message["input_text"]
        input_image_url: str = parsed_message["input_image_url"]
        input_metadata: dict[str, str] = InputBuilder().add_text_input(input_text)
        if input_image_url:
            input_metadata = input_metadata.add_image_input(input_image_url)
        input_metadata: dict[str, str] = input_metadata.build()

        print(f"Input Metadata: {input_metadata}")

        response: str = (
            PromptBuilder(client=self.openai_client)
            .set_input(input_metadata)
            .set_model(Models.GPT_4_1_MINI)
            .get_response()
        )

        await message.reply(
            content=response,
            mention_author=True,
        )

    def send_message(self, channel_id: int, content: str):
        channel = self.get_channel(channel_id)
        if channel:
            return channel.send(content)
        else:
            print(f"Channel with ID {channel_id} not found.")
            return None

    async def parse_message(self, message: Message) -> dict[str, str] | None:
        if not message:
            return None

        content: dict[str, Any] = {
            "author": message.author.name,
            "content": message.content,
            "attachment": self.get_image_attachment(message),
            "referenced_message": await self.get_referenced_message_info(message),
        }

        input_text: str = f"{content['content']}"
        input_image_url: str | None = None

        if content["referenced_message"]:
            ref_content: dict[str, Any] = content["referenced_message"]

            if ref_content["attachment"]:
                input_text += (
                    (
                        f" (Replying to image posted by {ref_content['author']} captioned: {ref_content['content']})"
                    )
                    if len(ref_content["content"]) > 0
                    else f" (Replying to {ref_content['author']})"
                )
                input_image_url = ref_content["attachment"]["url"]
            elif len(ref_content["content"]) > 0:
                input_text += (
                    f" (Replying to {ref_content['author']}: {ref_content['content']})"
                )
            else:
                input_text += f" (Replying to {ref_content['author']})"

        if content["attachment"] and not input_image_url:
            input_image_url = content["attachment"]["url"]

        return {
            "input_text": input_text,
            "input_image_url": input_image_url,
            "author": content["author"],
        }

    def get_image_attachment(self, message: Message) -> dict[str, str]:
        attachments: list[Attachment] = message.attachments
        pattern = re.compile(r".*\.(jpg|jpeg|png|webp)$", re.IGNORECASE)

        for attachment in attachments:
            if pattern.match(attachment.filename):
                return {
                    "url": attachment.url,
                }

        return None

    async def get_referenced_message_info(self, message: Message) -> dict[str, Any]:
        if message.reference and message.reference.message_id:
            ref_message: MessageReference = message.reference
            channel = self.get_channel(ref_message.channel_id)
            if channel:
                referenced_message: Message = await channel.fetch_message(
                    ref_message.message_id
                )
                return {
                    "author": referenced_message.author.name,
                    "content": referenced_message.content,
                    "attachment": self.get_image_attachment(referenced_message) or None,
                }

        return None
