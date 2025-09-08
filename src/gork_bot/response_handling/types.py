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
from enum import Enum
from typing import Self

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

    def get_prompt_text(self) -> str | None:
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
