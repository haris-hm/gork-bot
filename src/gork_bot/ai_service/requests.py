import random

from typing import Any

from gork_bot import OAI_CLIENT

from gork_bot.ai_service.types import Input, Instructions, Metadata, Response
from gork_bot.ai_service.enums import (
    DiscordLocation,
    GPT_Model,
    MessageRole,
    RequestReason,
)

from gork_bot.resource_management.config import BotConfig
from gork_bot.response_handling.types import ParsedMessage
from gork_bot.db_service.models import GorkGuild, GorkMedia, GorkMessageContext


class ResponseBuilder:
    def __init__(self, bot_config: BotConfig, message_context: GorkMessageContext):
        self._bot_config: BotConfig = bot_config
        self._message_context: GorkMessageContext = message_context

    def build_inputs(
        self,
        messages: list[ParsedMessage],
        model_instructions: Instructions,
        should_request_additions: bool = False,
    ) -> list[dict[str, Any]]:
        inputs: list[Input] = [Input.from_instructions(model_instructions)]
        guild_context: GorkGuild | None = self._message_context.guild
        media_context: GorkMedia = self._message_context.media

        # Exclude last message to add developer messages before it
        for message in messages[:-1]:
            inputs.extend(
                Input.from_parsed_message(
                    discord_message=message,
                )
            )

        if guild_context.should_post_media:
            custom_media_tags: set[str] = media_context.get_media_tags()
            media_instructions: str = self._bot_config.get_instructions(
                tags=custom_media_tags
            )
            inputs.append(Input.from_string(media_instructions, MessageRole.DEVELOPER))

        if guild_context.should_request_additions:
            if random.random() < guild_context.addition_chance:
                addition: str = guild_context.get_prompt_addition()
                if addition:
                    inputs.append(Input.from_string(addition, MessageRole.DEVELOPER))

        inputs.extend(
            Input.from_parsed_message(
                messages[-1],
            )
        )

        return [input.body for input in inputs]

    def get_chat_completion(
        self,
        requestor: str,
        location: DiscordLocation,
        discord_messages: list[ParsedMessage],
    ) -> Response:
        model_name: str = self._bot_config.model
        model_instructions: Instructions = Instructions(
            identity=self._bot_config.identity,
            instructions=self._bot_config.instructions,
        )

        metadata: Metadata = Metadata(
            reason=RequestReason.CHAT_COMPLETION,
            location=location,
            requestor=requestor,
        )

        model_temperature: float = (
            self._bot_config.temperature if "gpt-5" not in model_name else None
        )

        if not model_name or not model_instructions:
            raise ValueError("Model and input must be set before getting a response.")

        return self.request_response(
            model=GPT_Model(model_name),
            instructions=model_instructions,
            message_history=discord_messages,
            metadata=metadata,
            max_output_tokens=self._bot_config.max_tokens,
            temperature=model_temperature,
            request_additions=True,
        )

    def request_response(
        self,
        model: GPT_Model,
        instructions: Instructions,
        message_history: list[ParsedMessage],
        metadata: Metadata,
        max_output_tokens: int,
        temperature: float,
        request_additions: bool = False,
    ) -> Response:
        model_temperature: float = temperature if "gpt-5" not in model.value else None

        response = OAI_CLIENT.responses.create(
            model=model.value,
            input=self.build_inputs(message_history, instructions, request_additions),
            max_output_tokens=max_output_tokens,
            temperature=model_temperature,
            metadata=metadata.get_metadata(),
            store=True,
        )

        return Response(
            text=response.output_text,
            message_context=self._message_context,
        )
