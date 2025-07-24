import traceback

from discord import (
    Intents,
    Message,
    Client,
    Embed,
    DMChannel,
    TextChannel,
    ChannelType,
    User,
)
from discord.threads import Thread
from typing import Any

from gork_bot.ai_requests import ResponseBuilder, Response
from gork_bot.message_parsing import ParsedMessage
from gork_bot.config import BotConfig, AIConfig
from gork_bot.user_manager import UserInfo


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

        channel: TextChannel | DMChannel | Thread | Any = message.channel
        channel_type: ChannelType | None = (
            channel.type if hasattr(channel, "type") else None
        )

        try:
            match channel_type:
                case ChannelType.text:
                    if not (
                        self.user in message.mentions
                        and self._bot_config.can_message_channel(channel)
                    ):
                        return

                    await self.handle_response(message)
                case ChannelType.private:
                    await self.handle_response(message, should_reply=False)
                case ChannelType.public_thread | ChannelType.private_thread:
                    if isinstance(channel, Thread):
                        if (
                            not channel.owner
                            or channel.owner != self.user
                            or not channel.me
                        ):
                            return

                        await self.handle_response(message, should_reply=False)
                    pass
                case _:
                    raise ValueError(f"Unsupported channel type: {channel_type}")
        except Exception:
            if isinstance(channel, DMChannel) or self._bot_config.can_message_channel(
                channel
            ):
                await message.reply(
                    content="An unexpected error occurred while processing your message. Please try again later.",
                    mention_author=False,
                    silent=True,
                    delete_after=60,
                )

            print(
                f"Error processing message from {message.author.name}: {traceback.format_exc()}"
            )

    def rate_limit_check(self, message: Message) -> bool:
        author: User = message.author
        author_id: int = author.id

        if author.id not in self._user_info.keys():
            self._user_info[author_id] = UserInfo(user_id=author_id, name=author.name)

        user: UserInfo = self._user_info.get(author_id)

        return user.update_message_stats(message, self._bot_config)

    async def handle_response(self, message: Message, should_reply: bool = True):
        if self.__testing:
            await self.send_message(
                should_reply=should_reply,
                original_message=message,
                content="Testing mode is enabled. No response will be sent.",
            )
            return

        if not self.rate_limit_check(message):
            await message.reply(
                content="You have exceeded the allowed number of messages. Please try again later.",
                mention_author=False,
                silent=True,
                delete_after=60,
            )
            return

        async with message.channel.typing():
            parsed_messages: list[ParsedMessage] = []
            referenced_message: ParsedMessage | None = None

            if isinstance(message.channel, Thread):
                message_history = reversed(
                    [msg async for msg in message.channel.history(limit=10)]
                )
                for msg in message_history:
                    parsed_msg: ParsedMessage = await ParsedMessage.parse(
                        self, msg, get_reference=False
                    )
                    parsed_messages.append(parsed_msg[0])
            else:
                parsed_messages = await ParsedMessage.parse(self, message)
                referenced_message = (
                    parsed_messages[0] if len(parsed_messages) > 1 else None
                )

            response_builder: ResponseBuilder = ResponseBuilder(
                self._ai_config, parsed_messages, message.author.name
            )

            await self.handle_default_output(
                message,
                response_builder,
                should_reply=should_reply,
                referenced_message=referenced_message,
            )

    async def handle_default_output(
        self,
        message: Message,
        response_builder: ResponseBuilder,
        should_reply: bool,
        referenced_message: ParsedMessage | None = None,
    ):
        response: Response = response_builder.get_response()
        embed: Embed | None = None

        if response.gif:
            embed = Embed()
            embed.set_image(url=response.gif)

        await self.create_thread(message, referenced_message)
        await self.send_message(
            should_reply,
            message,
            content=response.get_text(),
            embed=embed,
        )

    async def create_thread(
        self, message: Message, referenced_message: ParsedMessage
    ) -> Thread | None:
        if not (referenced_message and referenced_message.from_this_bot) or isinstance(
            message.channel, Thread
        ):
            return None

        # TODO: Make an AI request to generate a thread name based on the message content
        thread_name = f"Follow-up Discussion with {message.author.name}"
        thread = await message.create_thread(
            name=thread_name,
            auto_archive_duration=60,
            reason="Creating a thread for follow-up discussion.",
        )
        return thread

    async def send_message(
        self,
        should_reply: bool,
        original_message: Message,
        content: str,
        embed: Embed | None = None,
    ):
        if should_reply and not original_message.thread:
            return await original_message.reply(
                content=content,
                mention_author=False,
                embed=embed,
            )
        elif original_message.thread:
            return await original_message.thread.send(
                content=content,
                embed=embed,
            )
        else:
            return await original_message.channel.send(
                content=content,
                embed=embed,
            )
