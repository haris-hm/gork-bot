import requests
import json
import random
import dotenv
import os
import re

from openai import OpenAI
from PIL import Image
from io import BytesIO
from base64 import b64encode

from gork_bot.config import AIConfig
from gork_bot.media_manager import CustomMediaStore

dotenv.load_dotenv()
OPENAI_API_KEY: str = os.getenv("OPENAI_KEY")
GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY")
CLIENT_KEY: str = os.getenv("CLIENT_KEY", "gork_bot")

CLIENT: OpenAI = OpenAI(api_key=OPENAI_API_KEY)


class Models:
    GPT_4_1_MINI = "gpt-4.1-mini"
    GPT_4_O_MINI = "gpt-4o-mini"


class Response:
    def __init__(self, text: str, media_store: CustomMediaStore):
        self.text: str = text
        self.gif: str | None = self.set_gif(media_store)

    def set_gif(self, media_store: CustomMediaStore) -> str | None:
        if self.text:
            pattern: re.Pattern = re.compile(r"%%([^%]+)%%")
            matches: list[str] = pattern.findall(self.text)
            if matches:
                for match in matches:
                    self.text = self.text.replace(f"%%{match}%%", "")
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


class ResponseBuilder:
    def __init__(self, config: AIConfig):
        self.__input: dict[str, str] = {"role": "user", "content": []}
        self.__config: AIConfig = config

    def add_text_input(self, text: str):
        if text:
            self.__input.get("content").append({"type": "input_text", "text": text})
        return self

    def add_image_input(self, image_url: str, quality: int = 256):
        encoded_image: str = self.__process_image(image_url, quality)
        self.__input.get("content").append(
            {"type": "input_image", "image_url": encoded_image}
        )
        return self

    def get_response(self) -> Response:
        if not self.__config.model or not self.__input:
            raise ValueError("Model and input must be set before getting a response.")

        response = CLIENT.responses.create(
            model=self.__config.model,
            input=[self.__input],
            instructions=self.__config.get_instructions(),
            max_output_tokens=self.__config.max_tokens,
            temperature=self.__config.temperature,
        )

        response: Response = Response(
            text=response.output_text if hasattr(response, "output_text") else "",
            media_store=self.__config.media_store,
        )

        return response

    def get_response_stream(self) -> str:
        if not self.__config.model or not self.__input:
            raise ValueError("Model and input must be set before getting a response.")

        stream = CLIENT.responses.create(
            model=self.__config.model,
            input=[self.__input],
            instructions=self.__config.get_instructions(),
            max_output_tokens=self.__config.max_tokens,
            temperature=self.__config.temperature,
            stream=True,
        )

        return stream

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
