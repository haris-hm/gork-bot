import requests
import json
import random
import dotenv
import os

from openai import OpenAI
from PIL import Image
from io import BytesIO
from base64 import b64encode
from typing import Any

dotenv.load_dotenv()
OPENAI_API_KEY: str = os.getenv("OPENAI_KEY")

CLIENT: OpenAI = OpenAI(api_key=OPENAI_API_KEY)


class Models:
    GPT_4_1_MINI = "gpt-4.1-mini"
    GPT_4_O_MINI = "gpt-4o-mini"


class ResponseBuilder:
    def __init__(self, config_path: str):
        self.__input: dict[str, str] = {"role": "user", "content": []}
        self.__model: str = Models.GPT_4_1_MINI
        self.__max_tokens: int = 500
        self.__temperature: float = 0.7
        self.__instructions: str = self.__load_config(config_path)

    def set_model(self, model: str):
        if model:
            self.__model = model
        return self

    def set_max_tokens(self, max_tokens: int):
        if max_tokens > 0:
            self.__max_tokens = max_tokens
        return self

    def set_temperature(self, temperature: float):
        if 0 <= temperature <= 1:
            self.__temperature = temperature
        return self

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
        aspect_ratio: float = width / height
        height_larger: bool = height > width
        new_width, new_height = (0, 0)
        if height_larger:
            new_height = clamped_size
            new_width = int(aspect_ratio * new_height)
        else:
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

    def __load_config(self, config_path: str) -> str:
        instructions: str = ""

        with open(config_path, "r", encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)

            instructions = data.get("instructions", "")
            random_additions: list[str] = data.get("potential_additions", [])
            addition_chance: float = data.get("addition_chance", 0.2)
            self.set_model(data.get("model", Models.GPT_4_1_MINI))
            self.set_max_tokens(data.get("max_tokens", 500))
            self.set_temperature(data.get("temperature", 0.8))

            if random_additions and random.random() < addition_chance:
                instructions += f" {random.choice(random_additions)}"

        return instructions

    def get_response(self) -> str:
        if not self.__model or not self.__input:
            raise ValueError("Model and input must be set before getting a response.")

        response = CLIENT.responses.create(
            model=self.__model,
            input=[self.__input],
            instructions=self.__instructions,
            max_output_tokens=self.__max_tokens,
            temperature=self.__temperature,
        )

        return (
            response.output_text
            if response and hasattr(response, "output_text")
            else ""
        )
