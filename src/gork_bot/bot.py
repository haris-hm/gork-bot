import asyncio
import traceback

from discord import Intents, Message, Client, Embed, DMChannel, TextChannel
from openai.types.responses import ResponseTextDeltaEvent, ResponseTextDoneEvent
from typing import Any

from gork_bot.ai_requests import ResponseBuilder, Response
from gork_bot.message_parsing import ParsedMessage
from gork_bot.config import BotConfig, AIConfig
from gork_bot.user_manager import UserInfo, rate_limit_check


class GorkBot(Client):
    def __init__(
        self, prompt_config_path: str, bot_config_path: str, testing: bool = False
    ):
        intents = Intents.default()
        intents.guild_messages = True
        intents.message_content = True
        intents.messages = True
        intents.guilds = True

        self.__testing: bool = testing

        self._user_info: dict[int, UserInfo] = {}
        self._ai_config = AIConfig(prompt_config_path)
        self._bot_config = BotConfig(bot_config_path)

        if self._bot_config.stream_output and self._ai_config.post_media:
            raise ValueError(
                "Media posting is not supported in streaming mode. Please disable streaming or set post_media to False."
            )

        super().__init__(intents=intents)

    async def on_message(self, message: Message):
        if message.author == self.user:
            return

        channel: TextChannel | DMChannel | Any = message.channel

        try:
            if isinstance(channel, DMChannel):
                await self.handle_response(message, should_reply=False)

            elif isinstance(channel, TextChannel):
                if not (
                    self.user in message.mentions
                    and self._bot_config.can_message_channel(channel)
                ):
                    return

                await self.handle_response(message)
            else:
                raise ValueError(f"Unsupported channel type: {type(channel)}")
        except Exception:
            await message.reply(
                content="An unexpected error occurred while processing your message. Please try again later.",
                mention_author=False,
                silent=True,
                delete_after=60,
            )

            print(
                f"Error processing message from {message.author.name}: {traceback.format_exc()}"
            )

    @rate_limit_check
    async def handle_response(self, message: Message, should_reply: bool = True):
        parsed_message: ParsedMessage = await ParsedMessage.create(self, message)
        response_builder: ResponseBuilder = ResponseBuilder(self._ai_config)

        response_builder.add_text_input(parsed_message.input_text)
        if parsed_message.input_image_url:
            response_builder.add_image_input(parsed_message.input_image_url, 256)

        if self._bot_config.stream_output:
            await self.handle_streaming_output(
                response_builder, message, should_reply=should_reply
            )
        else:
            await self.handle_default_output(
                message, response_builder, should_reply=should_reply
            )

    async def handle_streaming_output(
        self, response_builder: ResponseBuilder, message: Message, should_reply: bool
    ):
        response: Message | None = None
        partial_response: str = ""
        last_edit: int = 0

        for chunk in response_builder.get_response_stream():
            if isinstance(chunk, ResponseTextDeltaEvent):
                partial_response += chunk.delta
                now = asyncio.get_event_loop().time()

                if response is None:
                    response = await self.send_message(
                        should_reply,
                        message,
                        content=partial_response,
                    )

                    last_edit = now
                elif now - last_edit > self._bot_config.stream_edit_interval_secs:
                    await response.edit(content=partial_response)
                    last_edit = now
            elif isinstance(chunk, ResponseTextDoneEvent):
                partial_response = chunk.text

                if response is None:
                    response = await self.send_message(
                        should_reply,
                        message,
                        content=partial_response,
                    )
                else:
                    await response.edit(content=partial_response)

    async def handle_default_output(
        self, message: Message, response_builder: ResponseBuilder, should_reply: bool
    ):
        response: Response = response_builder.get_response()
        embed: Embed | None = None

        if response.gif:
            embed = Embed()
            embed.set_image(url=response.gif)

        await self.send_message(
            should_reply,
            message,
            content=response.text,
            embed=embed,
        )

    async def send_message(
        self,
        should_reply: bool,
        original_message: Message,
        content: str,
        embed: Embed | None = None,
    ):
        if should_reply:
            return await original_message.reply(
                content=content,
                mention_author=False,
                embed=embed,
            )
        else:
            return await original_message.channel.send(
                content=content,
                embed=embed,
            )
