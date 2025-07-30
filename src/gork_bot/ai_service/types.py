import json
import random
import re
import requests

from base64 import b64encode
from io import BytesIO
from PIL import Image
from typing import Any, Self

from gork_bot import CLIENT_KEY, GOOGLE_API_KEY

from gork_bot.ai_service.enums import DiscordLocation, MessageRole, RequestReason

from gork_bot.resource_management.resource_stores import CustomMediaStore

from gork_bot.response_handling.types import ParsedMessage


class Metadata:
    def __init__(
        self, reason: RequestReason, location: DiscordLocation, requestor: str
    ):
        self.reason: RequestReason = reason
        self.requestor: str = requestor
        self.location: DiscordLocation = location

    def get_metadata(self) -> dict[str, str]:
        return {
            "reason": self.reason.value,
            "location": self.location.value,
            "requestor": self.requestor,
        }


class Instructions:
    def __init__(self, identity: str, instructions: str):
        self.identity: str = identity.strip()
        self.instructions: str = instructions.strip()

    def get_instructions(self) -> str:
        """
        Returns the instructions as a formatted string.
        """
        return f"# Identity\n\n {self.identity}\n# Instructions\n\n{self.instructions}"


class Response:
    def __init__(self, text: str, media_store: CustomMediaStore):
        self.__keyword_tag_pattern: re.Pattern = re.compile(r"%%([^%]+)%%")

        self.text: str = text
        self.gif: str | None = self.set_gif(media_store)

    def get_text(self) -> str:
        formatted_text: str = self.text.strip()
        formatted_text = re.sub(self.__keyword_tag_pattern, "", formatted_text)
        return formatted_text.strip()

    def set_gif(self, media_store: CustomMediaStore) -> str | None:
        if self.text:
            matches: list[str] = self.__keyword_tag_pattern.findall(self.text)
            if matches:
                for match in matches:
                    gif_links: list[str] = media_store.get_gif(match)

                    if gif_links:
                        return random.choice(gif_links)
                    else:
                        return self.get_internet_gif(keywords=match)

        return None

    def get_internet_gif(self, keywords: str) -> str:
        gif_limit: int = 10
        search_query = keywords.replace(" ", "+")
        search_url: str = f"https://tenor.googleapis.com/v2/search?q={search_query}&key={GOOGLE_API_KEY}&client_key={CLIENT_KEY}&limit={gif_limit}"

        response = requests.get(search_url)
        if response.status_code != 200:
            return None

        data = json.loads(response.content)

        if "results" not in data or not data["results"]:
            return None

        choice = random.choice(data["results"])

        gif = choice.get("media_formats").get("gif").get("url")

        if not gif:
            return None

        return gif


class Input:
    def __init__(self, role: MessageRole):
        self.role: MessageRole = role
        self.body: dict[str, Any] = {"role": role.value, "content": []}

    @classmethod
    def from_parsed_message(cls, discord_message: ParsedMessage) -> Self:
        """
        Creates a Message instance from a ParsedMessage.
        """
        message = cls(
            role=MessageRole.ASSISTANT
            if discord_message.from_this_bot
            else MessageRole.USER
        )

        input_text: str = discord_message.get_prompt_text()
        input_image_url: str | None = discord_message.get_prompt_image_url()

        if input_text:
            message._add_text_content(input_text)

        if input_image_url:
            message._add_image_content(input_image_url)

        return message

    @classmethod
    def from_string(cls, content: str, role: MessageRole = MessageRole.USER) -> Self:
        """
        Creates a Message instance from a string content.
        """
        message = cls(role=role)
        message._add_text_content(content)
        return message

    @classmethod
    def from_instructions(cls, instructions: Instructions) -> Self:
        """
        Creates a Message instance from Instructions.
        """
        message = cls(role=MessageRole.DEVELOPER)
        message._add_text_content(instructions.get_instructions())
        return message

    def _add_text_content(self, text: str):
        """
        Adds text content to the message.
        """
        if text:
            match self.role:
                case MessageRole.USER | MessageRole.DEVELOPER:
                    self.body["content"].append({"type": "input_text", "text": text})
                case MessageRole.ASSISTANT:
                    self.body["content"].append({"type": "output_text", "text": text})

    def _add_image_content(self, image_url: str):
        """
        Adds image content to the message.
        """
        if image_url:
            self.body["content"].append(
                {
                    "type": "input_image",
                    "image_url": self.__process_image(image_url, 256),
                }
            )

    def __process_image(self, image_url: str, clamped_size: int) -> str:
        if not image_url:
            raise ValueError("Image URL cannot be empty.")

        response = requests.get(image_url)
        image: Image.Image = Image.open(BytesIO(response.content))
        image = self.__resize_image(image, clamped_size)

        return self.__encode_image(image)

    def __resize_image(
        self, image: Image.Image, clamped_size: int = 256
    ) -> Image.Image:
        width, height = image.size
        height_larger: bool = height > width
        new_width, new_height = (0, 0)
        if height_larger:
            aspect_ratio: float = width / height
            new_height = clamped_size
            new_width = int(aspect_ratio * new_height)
        else:
            aspect_ratio: float = height / width
            new_width = clamped_size
            new_height = int(aspect_ratio * new_width)

        return image.resize((new_width, new_height), Image.LANCZOS)

    def __encode_image(self, image: Image.Image) -> str:
        buffered = BytesIO()
        img = image

        if img.mode == "RGBA":
            img = img.convert("RGB")

        img.save(buffered, format="JPEG")
        base64_image = b64encode(buffered.getvalue()).decode("utf-8")

        return f"data:image/jpeg;base64,{base64_image}"

    def __repr__(self):
        return f"Message(role={self.body['role']}, content={self.body['content']})"
