import traceback

from asyncio import create_task, sleep
from discord import Activity, Client, DMChannel, Intents, Guild, Message, Thread
from functools import wraps

from gork_bot.resource_management.config import AIConfig, BotConfig
from gork_bot.resource_management.resource_stores import PresenceMessageStore

from gork_bot.response_handling.types import ParsedMessage, UserInfo
from gork_bot.response_handling.responses import ResponseHandler

from gork_bot.db_service.models import GorkGuild


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

    async def setup_hook(self):
        self.presence_task = create_task(self._update_presence())

    async def on_message(self, message: Message):
        if message.author == self.user:
            return

        channel: DMChannel | Thread | None = message.channel
        guild: Guild | None = message.guild if message.guild else None

        async with channel.typing():
            try:
                gork_guild: GorkGuild | None = (
                    GorkGuild.get_by_id(guild.id) if guild else None
                )

                if not gork_guild and guild:
                    gork_guild = GorkGuild.create(
                        guild_id=guild.id,
                        guild_name=guild.name,
                        channel_allowlist_enabled=True,
                        timeout_interval_mins=10,
                        allowed_messages_per_interval=30,
                    )

                response_handler: ResponseHandler = ResponseHandler(
                    message=ParsedMessage(message, self.user),
                    ai_config=self._ai_config,
                    bot_config=self._bot_config,
                    user_info=self._user_info,
                    testing=self.__testing,
                    guild=GorkGuild.get_by_id(guild.id) if guild else None,
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

    async def _update_presence(self):
        await self.wait_until_ready()
        presence_store = PresenceMessageStore(self._bot_config.presence_message_path)

        while True:
            try:
                presence_message: Activity = (
                    presence_store.get_random_presence_message()
                )
                await self.change_presence(activity=presence_message)
            except Exception as e:
                print(f"Error updating presence: {e}")
            await sleep(self._bot_config.presence_message_interval_mins * 60)
