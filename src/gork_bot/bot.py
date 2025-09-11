import traceback

from asyncio import create_task, sleep
from discord import (
    Activity,
    DMChannel,
    Intents,
    Interaction,
    Member,
    Message,
    Thread,
    User,
)

from discord.ext.commands import Bot

from gork_bot.resource_management.config import BotConfig
from gork_bot.resource_management.resource_stores import PresenceMessageStore

from gork_bot.response_handling.types import ParsedMessage
from gork_bot.response_handling.responses import ResponseHandler

from gork_bot.db_service.models import GorkGuild


class GorkBot(Bot):
    def __init__(self, bot_config_path: str, testing: bool = False):
        intents = Intents.default()
        intents.guild_messages = True
        intents.message_content = True
        intents.messages = True
        intents.guilds = True
        super().__init__(command_prefix="", intents=intents)

        self.testing: bool = testing
        self.bot_config = BotConfig(bot_config_path)

    async def setup_hook(self):
        self.presence_task = create_task(self._update_presence())
        await self.tree.sync()

    async def on_message(self, message: Message):
        author: User | Member = message.author

        if author == self.user:
            return

        try:
            response_handler: ResponseHandler = ResponseHandler(
                message=ParsedMessage(message=message, bot_user=self.user),
                bot_config=self.bot_config,
                testing=self.testing,
            )

            await response_handler.handle_response()

        except Exception:
            if isinstance(message.channel, (DMChannel, Thread)):
                await self._send_error_message(message)
            elif message.guild is not None:
                guild: GorkGuild = GorkGuild.get_by_id(guild_id=message.guild.id)

                if not guild.channel_allowlist_enabled or guild.channel_allowed(
                    channel_id=message.channel.id
                ):
                    await self._send_error_message(message)

    async def _update_presence(self):
        await self.wait_until_ready()
        presence_store = PresenceMessageStore(self.bot_config.presence_message_path)

        while True:
            try:
                presence_message: Activity = (
                    presence_store.get_random_presence_message()
                )
                await self.change_presence(activity=presence_message)
            except Exception as e:
                print(f"Error updating presence: {e}")
            await sleep(self.bot_config.presence_message_interval_mins * 60)

    async def _send_error_message(self, message: Message):
        await message.reply(
            content="An unexpected error occurred while processing your message. Please try again later.",
            mention_author=False,
            silent=True,
            delete_after=60,
        )

        print(
            f"Error processing message from {message.author.name}: {traceback.format_exc()}"
        )


def setup_commands(bot: GorkBot):
    @bot.tree.command(name="echo", description="Echos the provided message.")
    async def __echo_command(interaction: Interaction, message: str):
        await interaction.response.send_message(message)
