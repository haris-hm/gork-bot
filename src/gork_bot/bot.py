import traceback

from discord import (
    Intents,
    Message,
    Client,
    DMChannel,
)
from discord.threads import Thread

from gork_bot.message_parsing import ParsedMessage
from gork_bot.config import BotConfig, AIConfig
from gork_bot.response_handling import UserInfo, ResponseHandler


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

        super().__init__(intents=intents)

    async def on_message(self, message: Message):
        if message.author == self.user:
            return

        try:
            response_handler: ResponseHandler = ResponseHandler(
                message=ParsedMessage(message, self.user),
                ai_config=self._ai_config,
                bot_config=self._bot_config,
                user_info=self._user_info,
                testing=self.__testing,
            )

            await response_handler.handle_response()

        except Exception:
            if isinstance(
                message.channel, (DMChannel, Thread)
            ) or self._bot_config.can_message_channel(message.channel):
                await message.reply(
                    content="An unexpected error occurred while processing your message. Please try again later.",
                    mention_author=False,
                    silent=True,
                    delete_after=60,
                )

            print(
                f"Error processing message from {message.author.name}: {traceback.format_exc()}"
            )
