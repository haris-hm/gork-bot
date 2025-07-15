import re
import json

from discord import (
    Intents,
    Message,
    Client,
    Attachment,
    MessageReference,
    User,
    TextChannel,
)
from typing import Any
from datetime import datetime
from gork_bot.ai_requests import ResponseBuilder


class BotConfig:
    def __init__(self, config_path: str):
        with open(config_path, "r", encoding="utf-8") as f:
            config: dict[str, Any] = json.load(f)

            self.admins: list[int] = config.get("admins", [])
            self.channel_blacklist: list[int] = config.get("channel_blacklist", [])
            self.allowed_messages_per_interval: int = config.get(
                "allowed_messages_per_interval", 30
            )
            self.timeout_interval_mins: int = config.get("timeout_interval_mins", 10)

    def is_admin(self, user: User) -> bool:
        return user.id in self.admins

    def can_message_channel(self, channel: TextChannel) -> bool:
        return channel.id not in self.channel_blacklist


class UserInfo:
    def __init__(self, user_id: int, name: str):
        self.user_id: int = user_id
        self.name: str = name
        self.messages_in_last_hour: int = 0
        self.last_message_time: datetime | None = None

    def __repr__(self):
        return f"UserInfo(user_id={self.user_id}, name='{self.name}')"

    def update_message_stats(self, message: Message, config: BotConfig) -> bool:
        if config.is_admin(message.author):
            return True

        message_time: datetime = message.created_at

        if (
            self.last_message_time is None
            or (message_time - self.last_message_time).total_seconds()
            > 60 * config.timeout_interval_mins
        ):
            self.messages_in_last_hour = 1
            self.last_message_time = message_time
        else:
            self.messages_in_last_hour += 1

        return self.messages_in_last_hour <= config.allowed_messages_per_interval


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
        self.input_text = self.content.strip().replace(
            "<@1394485692721008640>", "@Gork"
        )
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

            if reference.attachment.url:
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
    def __init__(self, prompt_config_path: str, bot_config_path: str):
        intents = Intents.default()
        intents.guild_messages = True
        intents.message_content = True
        intents.messages = True
        intents.guilds = True

        self.__prompt_config_path = prompt_config_path
        self.__bot_config = BotConfig(bot_config_path)
        self.__user_info: dict[int, UserInfo] = {}

        super().__init__(intents=intents)

    async def on_message(self, message: Message):
        if message.author == self.user or self.user not in message.mentions:
            return

        author: User = message.author

        if author.id not in self.__user_info.keys():
            self.__user_info[author.id] = UserInfo(user_id=author.id, name=author.name)

        user_info: UserInfo = self.__user_info[author.id]

        if not user_info.update_message_stats(message, self.__bot_config):
            await message.reply(
                content=f"Slow down, {author.mention}! You can only send {self.__bot_config.allowed_messages_per_interval} messages every {self.__bot_config.timeout_interval_mins} minute(s).",
                mention_author=False,
                silent=True,
                delete_after=60,
            )
            return

        async with message.channel.typing():
            await self.respond_to_message(message, testing=True)

    async def respond_to_message(self, message: Message, testing: bool = False):
        if testing:
            await message.reply(
                content="This is a test response. The bot is working correctly.",
                mention_author=False,
                silent=True,
            )
            return

        parsed_message: ParsedMessage = await ParsedMessage.create(self, message)
        response_builder: ResponseBuilder = ResponseBuilder(self.__prompt_config_path)

        response_builder.add_text_input(parsed_message.input_text)
        if parsed_message.input_image_url:
            response_builder.add_image_input(parsed_message.input_image_url, 256)

        response: str = response_builder.get_response()

        await message.reply(
            content=response,
            mention_author=False,
        )
