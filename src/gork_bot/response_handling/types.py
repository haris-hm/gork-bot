from datetime import datetime
import re

from discord import (
    Attachment,
    ChannelType,
    DMChannel,
    Embed,
    Message,
    MessageReference,
    Thread,
    TextChannel,
    User,
)
from typing import Self
from enum import Enum

from gork_bot.resource_management.config import BotConfig

YT_LINK_PATTERN: re.Pattern = re.compile(
    r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/(watch\?v=|embed/|v/|shorts/)?([A-Za-z0-9_-]{11})",
    re.IGNORECASE,
)
TWITTER_LINK_PATTERN: re.Pattern = re.compile(
    r"(https?://)?(www\.)?(twitter\.com|x\.com)/([A-Za-z0-9_]+)/status/(\d+)",
    re.IGNORECASE,
)


class EmbedType(Enum):
    YOUTUBE = "youtube"
    TWITTER = "twitter"
    UNKNOWN = "unknown"


class ParsedEmbed:
    def __init__(self, embed: Embed):
        self.embed_type: EmbedType = self.__determine_embed_type(embed)

        if self.embed_type != EmbedType.UNKNOWN:
            self.author: str = embed.author.name if embed.author else "Unknown"

            self.content: str = ""
            self.image_url: str = ""

            match self.embed_type:
                case EmbedType.YOUTUBE:
                    self.content = embed.title if embed.title else "No Title"
                    self.image_url = embed.thumbnail.url if embed.thumbnail else ""
                case EmbedType.TWITTER:
                    self.content = (
                        embed.description if embed.description else "No Description"
                    )
                    self.image_url = embed.image.url if embed.image else ""

    def __determine_embed_type(self, embed: Embed) -> EmbedType:
        if embed.url and re.match(YT_LINK_PATTERN, embed.url):
            return EmbedType.YOUTUBE
        elif embed.url and re.match(TWITTER_LINK_PATTERN, embed.url):
            return EmbedType.TWITTER
        return EmbedType.UNKNOWN

    def get_prompt_text(self) -> str:
        match self.embed_type:
            case EmbedType.YOUTUBE:
                return f"YouTube video by {self.author} titled '{self.content}'"
            case EmbedType.TWITTER:
                return (
                    f"Twitter post by {self.author} with the contents: '{self.content}'"
                )
            case EmbedType.UNKNOWN:
                return ""


class ParsedAttachment:
    def __init__(self, message: Message):
        self.image_urls: list[str] = self.__get_image_attachment(message.attachments)
        self.embeds: list[ParsedEmbed] = []
        if message.embeds:
            self.embeds = self.__parse_embeds(message.embeds)

    def __get_image_attachment(self, attachments: list[Attachment]) -> list[str]:
        image_urls: list[str] = []
        image_file_pattern = re.compile(r".*\.(jpg|jpeg|png|webp)$", re.IGNORECASE)

        for attachment in attachments:
            if image_file_pattern.match(attachment.filename):
                image_urls.append(attachment.url)

        return image_urls

    def __parse_embeds(self, embeds: list[Embed]) -> list[ParsedEmbed]:
        parsed_embeds: list[ParsedEmbed] = []
        for embed in embeds:
            parsed_embed: ParsedEmbed = ParsedEmbed(embed)
            if parsed_embed.embed_type != EmbedType.UNKNOWN:
                parsed_embeds.append(parsed_embed)

        return parsed_embeds


class ParsedMessage:
    __embed_url_pattern: re.Pattern = re.compile(
        f"{YT_LINK_PATTERN.pattern}|{TWITTER_LINK_PATTERN.pattern}",
        re.IGNORECASE,
    )

    def __init__(self, message: Message, bot_user: User):
        self.message_snowflake: Message = message
        self.bot_user: User = bot_user

        self.from_this_bot: bool = message.author == bot_user

        self.author: str = message.author.name
        self.content: str = message.content
        self.mentions: list[User] = message.mentions

        self.channel: TextChannel | DMChannel | Thread = message.channel
        self.channel_type: ChannelType = self.channel.type
        self.thread: Thread | None = (
            message.channel if isinstance(message.channel, Thread) else message.thread
        )

        if self.channel_type not in (
            ChannelType.text,
            ChannelType.private,
            ChannelType.public_thread,
        ):
            raise ValueError(
                f"Unsupported channel type: {self.channel.type}. "
                "ParsedMessage can only be used with text, DM, or public thread channels."
            )

        self.attachment: ParsedAttachment = ParsedAttachment(message)

    def get_prompt_text(self) -> str:
        message_conent: str = re.sub(self.__embed_url_pattern, "", self.content.strip())

        for user in self.mentions:
            message_conent = message_conent.replace(f"<@{user.id}>", f"@{user.name}")

        return message_conent.strip()

    def get_prompt_image_urls(self) -> str | None:
        return self.attachment.image_urls

    async def get_history(self, limit: int = 10) -> list[Self]:
        """
        Returns the history of messages in the thread if this message is part of a thread.
        """
        message_history: list[Self] = [self]

        if isinstance(self.channel, (Thread, DMChannel)):
            message_history: list[ParsedMessage] = [
                ParsedMessage(msg, self.bot_user)
                async for msg in self.channel.history(limit=limit)
            ]
            message_history = list(reversed(message_history))
        elif (
            self.message_snowflake.reference
            and self.message_snowflake.reference.message_id
        ):
            ref_message: MessageReference = self.message_snowflake.reference
            channel = self.message_snowflake.channel

            if channel:
                referenced_message: Message = await channel.fetch_message(
                    ref_message.message_id
                )
                message_history.insert(
                    0, ParsedMessage(referenced_message, self.bot_user)
                )

        return message_history

    def __repr__(self) -> str:
        return f"ParsedMessage(author={self.author}, content={self.content})"


class UserInfo:
    """Stores information about a user, including their ID, name, message count in the last hour for rate limiting purposes."""

    def __init__(self, user_id: int, name: str):
        """Initializes the UserInfo with the user's ID and name.

        :param user_id: The unique identifier for the user.
        :type user_id: int
        :param name: The name of the user.
        :type name: str
        """

        self.user_id: int = user_id
        self.name: str = name
        self.messages_in_last_hour: int = 0
        self.last_message_time: datetime | None = None

    def __repr__(self):
        return f"UserInfo(user_id={self.user_id}, name='{self.name}', messages_in_last_hour={self.messages_in_last_hour}, last_message_time={self.last_message_time})"

    def update_message_stats(self, message: Message, config: BotConfig) -> bool:
        """Updates the message statistics for the user and checks if they are within the allowed limits.

        :param message: The discord message sent by the user.
        :type message: Message
        :param config: The bot configuration containing rate limit settings.
        :type config: BotConfig
        :return: True if the user is within the allowed message limits, False otherwise.
        :rtype: bool
        """
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
