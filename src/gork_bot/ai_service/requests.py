from typing import Any

from gork_bot import OAI_CLIENT
from gork_bot.ai_service.types import Input, Metadata, Response
from gork_bot.ai_service.enums import DiscordLocation
from gork_bot.ai_service.enums import GPT_Model, MessageRole, RequestReason
from gork_bot.config import AIConfig
from gork_bot.message_parsing import ParsedMessage


class ResponseBuilder:
    def __init__(self, config: AIConfig, discord_messages: list[ParsedMessage]):
        self.__config: AIConfig = config
        self.__inputs: list[ParsedMessage] = discord_messages

    def build_inputs(self, model_instructions: str) -> list[dict[str, Any]]:
        inputs: list[Input] = [
            Input.from_string(content=model_instructions, role=MessageRole.DEVELOPER)
        ]

        for input in self.__inputs:
            inputs.append(
                Input.from_parsed_message(
                    input,
                )
            )

        return [input.body for input in inputs]

    def get_response(self, requestor: str, location: DiscordLocation) -> Response:
        model_name: str = self.__config.model
        model_instructions: str = self.__config.get_instructions()
        metadata: Metadata = Metadata(
            reason=RequestReason.CHAT_COMPLETION,
            location=location,
            requestor=requestor,
        )

        if not model_name or not model_instructions:
            raise ValueError("Model and input must be set before getting a response.")

        return self.request_response(
            model=GPT_Model(model_name),
            instructions=model_instructions,
            metadata=metadata,
        )

    def request_response(
        self,
        model: GPT_Model,
        instructions: str,
        metadata: Metadata,
    ) -> Response:
        response = OAI_CLIENT.responses.create(
            model=model.value,
            input=self.build_inputs(instructions),
            max_output_tokens=self.__config.max_tokens,
            temperature=self.__config.temperature,
            store=True,
            metadata=metadata.get_metadata(),
        )

        return Response(
            response.output_text,
            self.__config.media_store,
        )
