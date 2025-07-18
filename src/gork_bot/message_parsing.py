import re
import dotenv
import os

from googleapiclient.discovery import build
from typing import Any
from discord import Attachment, Message, MessageReference, Client

dotenv.load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


def get_youtube_link_pattern() -> re.Pattern:
    """
    Returns a compiled regex pattern to match YouTube video links.
    """
    return re.compile(
        r"(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([A-Za-z0-9_-]{11})"
    )


class ParsedYoutubeLinks:
    def __init__(self, content: str):
        self.video_ids: list[str] = set(get_youtube_link_pattern().findall(content))

        youtube = build("youtube", "v3", developerKey=GOOGLE_API_KEY)
        response = (
            youtube.videos().list(part="snippet", id=",".join(self.video_ids)).execute()
        )

        self.video_titles = [
            f"{item['snippet']['title']}" for item in response.get("items", [])
        ]


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
        self.__reference = None

        self.author: str = message.author.name
        self.content: str = message.content
        self.attachment: ParsedAttachment = ParsedAttachment(message)
        self.youtube_titles: ParsedYoutubeLinks | None = ParsedYoutubeLinks(
            message.content
        )
        self.input_text: str | None = None
        self.input_image_url: str = None

    @classmethod
    async def create(cls, client: Client, message: Message):
        self = cls(message)
        self.input_text = message.content.strip()

        for user in message.mentions:
            self.input_text = self.input_text.replace(f"<@{user.id}>", f"@{user.name}")

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
        self.input_text = re.sub(
            get_youtube_link_pattern(), "", self.input_text
        ).strip()

        if self.__reference:
            reference: ParsedMessage = self.__reference
            ref_content_empty: bool = len(reference.content) == 0

            if reference.attachment.image_url:
                if not ref_content_empty:
                    self.input_text += f" (Replying to image posted by {reference.author} captioned: {reference.content})"
                else:
                    self.input_text += (
                        f" (Replying to image posted by {reference.author})"
                    )
                self.input_image_url = reference.attachment.image_url
            elif not ref_content_empty:
                self.input_text += (
                    f" (Replying to {reference.author}: {reference.content})"
                )
            else:
                self.input_text += f" (Replying to {reference.author})"

            if self.__reference.youtube_titles.video_titles:
                self.input_text += f" (Linked YouTube video(s) in original message: {', '.join(self.__reference.youtube_titles.video_titles)})"

        if self.attachment and not self.input_image_url:
            self.input_image_url = self.attachment.image_url

        if self.youtube_titles.video_titles:
            self.input_text += f" (Linked YouTube video(s): {', '.join(self.youtube_titles.video_titles)})"
