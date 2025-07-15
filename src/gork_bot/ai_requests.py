import requests
from openai import OpenAI
from PIL import Image
import io
import base64


class Models:
    GPT_4_1_MINI = "gpt-4.1-mini"
    GPT_4_O_MINI = "gpt-4o-mini"


class InputBuilder:
    def __init__(self):
        self.input: dict[str, str] = {"role": "user", "content": []}

    def add_text_input(self, text: str):
        if text:
            self.input["content"].append({"type": "input_text", "text": text})
        return self

    def add_image_input(self, image_url: str, detail: str = "low"):
        if not image_url:
            raise ValueError("Image URL cannot be empty.")

        response = requests.get(image_url)
        img: Image.Image = Image.open(io.BytesIO(response.content))
        img = self.resize_image_keep_aspect(img)

        # Convert image to base64
        buffered = io.BytesIO()
        if img.mode == "RGBA":
            img = img.convert("RGB")
        img.save(buffered, format="JPEG")
        base64_image = base64.b64encode(buffered.getvalue()).decode("utf-8")
        data_url = f"data:image/jpeg;base64,{base64_image}"

        self.input["content"].append(
            {"type": "input_image", "image_url": data_url, "detail": detail}
        )
        return self

    def build(self) -> list[dict[str, str]]:
        if not self.input["content"]:
            raise ValueError("Input must contain at least one content item.")
        return [self.input]

    def resize_image_keep_aspect(
        self, img: Image.Image, target_height: int = 256
    ) -> Image.Image:
        width, height = img.size
        aspect_ratio = width / height
        new_height = target_height
        new_width = int(aspect_ratio * new_height)
        return img.resize((new_width, new_height), Image.LANCZOS)


class PromptBuilder:
    def __init__(self, client: OpenAI):
        self.client = client
        self.model = None
        self.input = None
        self.max_tokens = 1000
        self.temperature = 0.7

    def set_model(self, model: str):
        self.model = model
        return self

    def set_input(self, input: str):
        self.input = input
        return self

    def set_max_tokens(self, max_tokens: int):
        if max_tokens > 0:
            self.max_tokens = max_tokens
        return self

    def set_temperature(self, temperature: float):
        if 0 <= temperature <= 1:
            self.temperature = temperature
        return self

    def get_response(self) -> str:
        if not self.model or not self.input:
            raise ValueError("Model and input must be set before getting a response.")
        # return "AAAAAAAAAA"

        instructions = ""

        response = self.client.responses.create(
            model=self.model,
            input=self.input,
            instructions=instructions,
            max_output_tokens=self.max_tokens,
            temperature=self.temperature,
        )

        return (
            response.output_text
            if response and hasattr(response, "output_text")
            else ""
        )
