import asyncio

from discord import (
    Intents,
    Message,
    Client,
    User,
)
from openai.types.responses import ResponseTextDeltaEvent, ResponseTextDoneEvent
from datetime import datetime

from gork_bot.ai_requests import ResponseBuilder
from gork_bot.message_parsing import ParsedMessage
from gork_bot.config import BotConfig


class UserInfo:
    def __init__(self, user_id: int, name: str):
        self.user_id: int = user_id
        self.name: str = name
        self.messages_in_last_hour: int = 0
        self.last_message_time: datetime | None = None

    def __repr__(self):
        return f"UserInfo(user_id={self.user_id}, name='{self.name}')"

    def update_message_stats(self, message: Message, config: BotConfig) -> bool:
        if config.is_admin(message.author):
            return True

        message_time: datetime = message.created_at

        if (
            self.last_message_time is None
            or (message_time - self.last_message_time).total_seconds()
            > 60 * config.timeout_interval_mins
        ):
            self.messages_in_last_hour = 1
            self.last_message_time = message_time
        else:
            self.messages_in_last_hour += 1

        return self.messages_in_last_hour <= config.allowed_messages_per_interval


class GorkBot(Client):
    def __init__(self, prompt_config_path: str, bot_config_path: str):
        intents = Intents.default()
        intents.guild_messages = True
        intents.message_content = True
        intents.messages = True
        intents.guilds = True

        self.__prompt_config_path = prompt_config_path
        self.__bot_config = BotConfig(bot_config_path)
        self.__user_info: dict[int, UserInfo] = {}

        super().__init__(intents=intents)

    async def on_message(self, message: Message):
        if (
            message.author == self.user
            or self.user not in message.mentions
            or not self.__bot_config.can_message_channel(message.channel)
        ):
            return

        author: User = message.author

        if author.id not in self.__user_info.keys():
            self.__user_info[author.id] = UserInfo(user_id=author.id, name=author.name)

        user_info: UserInfo = self.__user_info[author.id]

        if not user_info.update_message_stats(message, self.__bot_config):
            await message.reply(
                content=f"Slow down, {author.mention}! You can only send {self.__bot_config.allowed_messages_per_interval} messages every {self.__bot_config.timeout_interval_mins} minute(s).",
                mention_author=False,
                silent=True,
                delete_after=60,
            )
            return

        async with message.channel.typing():
            await self.respond_to_message(message, testing=False)

    async def respond_to_message(self, message: Message, testing: bool = False):
        if testing:
            await message.reply(
                content="This is a test response. The bot is working correctly.",
                mention_author=False,
                silent=True,
            )
            return

        parsed_message: ParsedMessage = await ParsedMessage.create(self, message)
        response_builder: ResponseBuilder = ResponseBuilder(self.__prompt_config_path)

        response_builder.add_text_input(parsed_message.input_text)
        if parsed_message.input_image_url:
            response_builder.add_image_input(parsed_message.input_image_url, 256)

        if self.__bot_config.stream_output:
            reply = None
            partial_response = ""
            last_edit = 0

            for chunk in response_builder.get_response_stream():
                if isinstance(chunk, ResponseTextDeltaEvent):
                    partial_response += chunk.delta
                    now = asyncio.get_event_loop().time()

                    if reply is None:
                        reply = await message.reply(
                            content=partial_response,
                            mention_author=False,
                        )
                        last_edit = now
                    elif now - last_edit > self.__bot_config.stream_edit_interval_secs:
                        await reply.edit(content=partial_response)
                        last_edit = now
                elif isinstance(chunk, ResponseTextDoneEvent):
                    partial_response = chunk.text

                    if reply is None:
                        reply = await message.reply(
                            content=partial_response,
                            mention_author=False,
                        )
                    else:
                        await reply.edit(content=partial_response)
        else:
            response: str = response_builder.get_response()

            await message.reply(
                content=response,
                mention_author=False,
            )
