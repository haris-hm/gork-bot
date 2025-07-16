import requests
import dotenv
import os

from openai import OpenAI
from PIL import Image
from io import BytesIO
from base64 import b64encode

from gork_bot.config import AIConfig

dotenv.load_dotenv()
OPENAI_API_KEY: str = os.getenv("OPENAI_KEY")

CLIENT: OpenAI = OpenAI(api_key=OPENAI_API_KEY)


class Models:
    GPT_4_1_MINI = "gpt-4.1-mini"
    GPT_4_O_MINI = "gpt-4o-mini"


class ResponseBuilder:
    def __init__(self, config_path: str):
        self.__input: dict[str, str] = {"role": "user", "content": []}
        self.__config: AIConfig = AIConfig(config_path)

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

    def get_response(self) -> str:
        if not self.__config.model or not self.__input:
            raise ValueError("Model and input must be set before getting a response.")

        response = CLIENT.responses.create(
            model=self.__config.model,
            input=[self.__input],
            instructions=self.__config.get_instructions(),
            max_output_tokens=self.__config.max_tokens,
            temperature=self.__config.temperature,
        )

        return (
            response.output_text
            if response and hasattr(response, "output_text")
            else ""
        )

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
        image = self.__resize_image(image)

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
