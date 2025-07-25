import re
import dotenv
import os

from googleapiclient.discovery import build
from typing import Self
from discord import (
    Attachment,
    Message,
    MessageReference,
    Thread,
    User,
    Thread,
    TextChannel,
    DMChannel,
    ChannelType,
)

dotenv.load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


class ParsedYoutubeLinks:
    __yt_video_id_pattern: re.Pattern = re.compile(
        r"(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([A-Za-z0-9_-]{11})"
    )

    def __init__(self, content: str):
        self.video_ids: list[str] = set(self.__yt_video_id_pattern.findall(content))

        youtube = build("youtube", "v3", developerKey=GOOGLE_API_KEY)
        response = (
            youtube.videos().list(part="snippet", id=",".join(self.video_ids)).execute()
        )

        self.video_titles = [
            f"{item['snippet']['title']}" for item in response.get("items", [])
        ]

    def get_prompt_text(self) -> str:
        if not self.video_titles:
            return ""

        titles = ", ".join(self.video_titles)
        return f"(Linked YouTube video(s): {titles})" if titles else ""


class ParsedAttachment:
    def __init__(self, message: Message):
        self.image_url: str | None = self.__get_image_attachment(message.attachments)

    def __get_image_attachment(self, attachments: list[Attachment]) -> dict[str, str]:
        pattern = re.compile(r".*\.(jpg|jpeg|png|webp)$", re.IGNORECASE)

        for attachment in attachments:
            if pattern.match(attachment.filename):
                return attachment.url

        return None


class ParsedChannelInfo:
    def __init__(self, channel: TextChannel | DMChannel | Thread):
        self.channel: TextChannel | DMChannel | Thread = channel
        self.channel_id: int = channel.id
        self.channel_name: str = (
            channel.name if hasattr(channel, "name") else "DM Channel"
        )
        self.channel_type: ChannelType = channel.type

        if isinstance(channel, Thread):
            self.thread_id: int = channel.id
            self.thread_name: str = channel.name
            self.is_thread: bool = True
        else:
            self.thread_id = None
            self.thread_name = None
            self.is_thread: bool = False


class ParsedMessage:
    __yt_url_pattern: re.Pattern = re.compile(
        r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/(watch\?v=|embed/|v/|shorts/)?([A-Za-z0-9_-]{11})",
        re.IGNORECASE,
    )

    def __init__(self, message: Message, bot_user: User):
        if message.channel.type not in (
            ChannelType.text,
            ChannelType.private,
            ChannelType.public_thread,
            ChannelType.private_thread,
        ):
            raise ValueError(
                f"Unsupported channel type: {message.channel.type}. "
                "ParsedMessage can only be used with text, DM, or public/private thread channels."
            )

        self.message_snowflake: Message = message
        self.bot_user: User = bot_user

        self.from_this_bot: bool = message.author == bot_user

        self.author: str = message.author.name
        self.content: str = message.content
        self.mentions: list[User] = message.mentions

        self.attachment: ParsedAttachment = ParsedAttachment(message)
        self.youtube_titles: ParsedYoutubeLinks | None = ParsedYoutubeLinks(
            message.content
        )

    def get_prompt_text(self) -> str:
        message_conent: str = re.sub(self.__yt_url_pattern, "", self.content.strip())

        for user in self.mentions:
            message_conent = message_conent.replace(f"<@{user.id}>", f"@{user.name}")

        prompt_text: str = f"{self.author}: {message_conent}"
        if self.youtube_titles and self.youtube_titles.video_titles:
            prompt_text += f" {self.youtube_titles.get_prompt_text()}"

        return prompt_text.strip()

    def get_prompt_image_url(self) -> str | None:
        return self.attachment.image_url

    def get_channel_info(self) -> ParsedChannelInfo:
        """
        Returns the channel information for the message.
        """
        return ParsedChannelInfo(self.message_snowflake.channel)

    async def get_history(self, limit: int = 10) -> list[Self]:
        """
        Returns the history of messages in the thread if this message is part of a thread.
        """
        message_history: list[Self] = [self]

        if self.get_channel_info().is_thread:
            message_history = [
                ParsedMessage.parse(self.thread.client, msg)
                async for msg in self.thread.history(limit=limit)
            ]
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
