import re
import dotenv
import os

from googleapiclient.discovery import build
from typing import Self
from discord import Attachment, Message, MessageReference, Client

dotenv.load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


def get_youtube_link_pattern() -> re.Pattern:
    """
    Returns a compiled regex pattern to match YouTube video links.
    """
    return


class ParsedYoutubeLinks:
    def __init__(self, content: str):
        yt_video_id_pattern: re.Pattern = re.compile(
            r"(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([A-Za-z0-9_-]{11})"
        )
        self.video_ids: list[str] = set(yt_video_id_pattern.findall(content))

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


class ParsedMessage:
    def __init__(self, message: Message):
        self.original_message: Message = message
        self.author: str = message.author.name
        self.from_this_bot: bool = False
        self.content: str = message.content
        self.attachment: ParsedAttachment = ParsedAttachment(message)
        self.youtube_titles: ParsedYoutubeLinks | None = ParsedYoutubeLinks(
            message.content
        )

        self.input_text: str | None = None
        self.input_image_url: str = None

    @classmethod
    async def parse(
        cls, client: Client, message: Message, get_reference: bool = True
    ) -> list[Self]:
        yt_url_pattern: re.Pattern = re.compile(
            r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/(watch\?v=|embed/|v/|shorts/)?([A-Za-z0-9_-]{11})",
            re.IGNORECASE,
        )

        self = cls(message)
        self.from_this_bot = message.author == client.user
        self.input_text = re.sub(yt_url_pattern, "", message.content.strip())
        self.input_image_url = self.attachment.image_url

        for user in message.mentions:
            self.input_text = self.input_text.replace(f"<@{user.id}>", f"@{user.name}")

        messages: list[ParsedMessage] = [self]

        if get_reference:
            referenced_message: (
                ParsedMessage | None
            ) = await self.__define_referenced_message(client, message)

            if referenced_message:
                messages = [referenced_message, self]

        return messages

    def get_prompt_text(self) -> str:
        prompt_text: str = f"{self.author}: {self.input_text}"
        if self.youtube_titles and self.youtube_titles.video_titles:
            prompt_text += f" {self.youtube_titles.get_prompt_text()}"
        return prompt_text.strip()

    async def __define_referenced_message(
        self, client: Client, message: Message
    ) -> Self | None:
        if message.reference and message.reference.message_id:
            ref_message: MessageReference = message.reference
            channel = client.get_channel(ref_message.channel_id)

            if channel:
                referenced_message: Message = await channel.fetch_message(
                    ref_message.message_id
                )
                parsed_reference: ParsedMessage = await ParsedMessage.parse(
                    client, referenced_message, get_reference=False
                )

                return parsed_reference[0] if parsed_reference else None

        return None

    def __repr__(self) -> str:
        return f"ParsedMessage(author={self.author}, content={self.content})"
