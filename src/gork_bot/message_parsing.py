import re

from discord import (
    Attachment,
    ChannelType,
    DMChannel,
    Message,
    MessageReference,
    Thread,
    TextChannel,
    User,
)
from googleapiclient.discovery import build
from typing import Self

from gork_bot import GOOGLE_API_KEY


class ParsedYoutubeLinks:
    """Class to parse YouTube video links from a message content."""

    __yt_video_id_pattern: re.Pattern = re.compile(
        r"(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([A-Za-z0-9_-]{11})"
    )

    def __init__(self, content: str):
        """Initializes the ParsedYoutubeLinks with the content of a Discord message.
        Parses the content for YouTube video links and retrieves their titles using the YouTube Data API.

        :param content: The content of the Discord message to parse for YouTube video links.
        :type content: str
        """
        self.video_ids: list[str] = set(self.__yt_video_id_pattern.findall(content))

        youtube = build("youtube", "v3", developerKey=GOOGLE_API_KEY)
        response = (
            youtube.videos().list(part="snippet", id=",".join(self.video_ids)).execute()
        )

        self.video_titles = [
            f"{item['snippet']['title']}" for item in response.get("items", [])
        ]

    def get_prompt_text(self) -> str:
        """Generates a string representation of the YouTube video titles for use in
        the chat history of prompts.

        :return: A string containing the titles of the YouTube videos linked in the message.
        :rtype: str
        """
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


class ParsedMessage:
    __yt_url_pattern: re.Pattern = re.compile(
        r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/(watch\?v=|embed/|v/|shorts/)?([A-Za-z0-9_-]{11})",
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
        self.youtube_titles: ParsedYoutubeLinks | None = ParsedYoutubeLinks(
            message.content
        )

    def get_prompt_text(self) -> str:
        message_conent: str = re.sub(self.__yt_url_pattern, "", self.content.strip())

        for user in self.mentions:
            message_conent = message_conent.replace(f"<@{user.id}>", f"@{user.name}")

        if self.youtube_titles and self.youtube_titles.video_titles:
            message_conent += f" {self.youtube_titles.get_prompt_text()}"

        return message_conent.strip()

    def get_prompt_image_url(self) -> str | None:
        return self.attachment.image_url

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
            message_history = reversed(message_history)
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
