import re
from discord import Intents, Message, Client, Attachment, MessageReference
from typing import Any
from gork_bot.ai_requests import Models, ResponseBuilder


class ParsedAttachment:
    def __init__(self, attachments: list[Attachment]):
        self.url: str | None = self.__get_image_attachment(attachments)

    def __get_image_attachment(self, attachments: list[Attachment]) -> dict[str, str]:
        pattern = re.compile(r".*\.(jpg|jpeg|png|webp)$", re.IGNORECASE)

        for attachment in attachments:
            if pattern.match(attachment.filename):
                return attachment.url

        return None


class ParsedMessage:
    def __init__(self, message: Message):
        self.__reference = None

        self.author = message.author.name
        self.content = message.content
        self.attachment = ParsedAttachment(message.attachments)
        self.input_text = self.content
        self.input_image_url = None

    @classmethod
    async def create(cls, client: Client, message: Message):
        self = cls(message)
        self.__reference = await self.__get_referenced_message_info(client, message)
        self.__define_prompt_inputs()
        return self

    async def __get_referenced_message_info(
        self, client: Client, message: Message
    ) -> dict[str, Any]:
        if message.reference and message.reference.message_id:
            ref_message: MessageReference = message.reference
            channel = client.get_channel(ref_message.channel_id)

            if channel:
                referenced_message: Message = await channel.fetch_message(
                    ref_message.message_id
                )
                return ParsedMessage(referenced_message)

        return None

    def __define_prompt_inputs(self):
        if self.__reference:
            reference: ParsedMessage = self.__reference
            ref_content_empty: bool = len(reference.content) == 0

            if reference.attachment:
                if not ref_content_empty:
                    self.input_text += f" (Replying to image posted by {reference.author} captioned: {reference.content})"
                else:
                    self.input_text += (
                        f" (Replying to image posted by {reference.author})"
                    )
                self.input_image_url = reference.attachment.url
            elif not ref_content_empty:
                self.input_text += (
                    f" (Replying to {reference.author}: {reference.content})"
                )
            else:
                self.input_text += f" (Replying to {reference.author})"

        if self.attachment and not self.input_image_url:
            self.input_image_url = self.attachment.url


class GorkBot(Client):
    def __init__(self):
        intents = Intents.default()
        intents.guild_messages = True
        intents.message_content = True
        intents.messages = True
        intents.guilds = True

        super().__init__(intents=intents)

    async def on_message(self, message: Message):
        if message.author == self.user or self.user not in message.mentions:
            return

        async with message.channel.typing():
            parsed_message: ParsedMessage = await ParsedMessage.create(self, message)
            response_builder: ResponseBuilder = ResponseBuilder("config/prompts.json")

            response_builder.add_text_input(parsed_message.input_text)
            if parsed_message.input_image_url:
                response_builder.add_image_input(parsed_message.input_image_url, 256)
            response_builder.set_model(Models.GPT_4_1_MINI)

            response: str = response_builder.get_response()

            await message.reply(
                content=response,
                mention_author=False,
            )
