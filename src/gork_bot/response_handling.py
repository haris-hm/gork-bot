from discord import (
    Message,
    Thread,
    Embed,
    User,
    DMChannel,
    TextChannel,
    ChannelType,
)
from datetime import datetime
from typing import Any

from gork_bot.config import BotConfig, AIConfig
from gork_bot.ai_service import ResponseBuilder, Response
from gork_bot.message_parsing import ParsedMessage


class UserInfo:
    """Stores information about a user, including their ID, name, message count in the last hour for rate limiting purposes."""

    def __init__(self, user_id: int, name: str):
        self.user_id: int = user_id
        self.name: str = name
        self.messages_in_last_hour: int = 0
        self.last_message_time: datetime | None = None

    def __repr__(self):
        return f"UserInfo(user_id={self.user_id}, name='{self.name}', messages_in_last_hour={self.messages_in_last_hour}, last_message_time={self.last_message_time})"

    def update_message_stats(self, message: Message, config: BotConfig) -> bool:
        """
        Updates the message statistics for the user and checks if they are within the allowed limits.

        :param message: The discord message sent by the user.
        :type message: Message
        :param config: The bot configuration containing rate limit settings.
        :type config: BotConfig
        :return: True if the user is within the allowed message limits, False otherwise.
        :rtype: bool
        """
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


class ResponseHandler:
    """Handles sending responses to messages that the bot receives."""

    def __init__(
        self,
        message: ParsedMessage,
        bot_config: BotConfig,
        ai_config: AIConfig,
        user_info: dict[int, UserInfo],
        testing: bool = False,
    ):
        """Initializes the ResponseHandler with the necessary configurations and message.

        :param message: The parsed message that the bot received.
        :type message: ParsedMessage
        :param bot_config: The configuration for the bot, including rate limits and other settings.
        :type bot_config: BotConfig
        :param ai_config: The configuration for the AI, including model settings and instructions.
        :type ai_config: AIConfig
        :param user_info: The user info dictionary, storing rate limit information
        :type user_info: dict[int, UserInfo]
        :param testing: If the bot is currently in testing mode, defaults to False
        :type testing: bool, optional
        """
        self._bot_config: BotConfig = bot_config
        self._ai_config: AIConfig = ai_config
        self._user_info: dict[int, UserInfo] = user_info if user_info else {}
        self.__testing: bool = testing

        self.message: ParsedMessage = message

    async def send_response(
        self,
        content: str,
        should_reply: bool = False,
        mention_author: bool = False,
        embed: Embed | None = None,
        delete_after: float | None = None,
        silent: bool = False,
    ) -> Message:
        """
        Sends a response to the channel the original message was sent to. The response can be sent as a
        reply to the original message or as a new message in the same channel or thread.

        :param content: The content of the response message.
        :type content: str
        :param should_reply: If the response should be a direct reply to the original message, which means
        that the original message is referenced. Defaults to False.
        :type should_reply: bool, optional
        :param mention_author: If the author of the original message should be mentioned in the response,
        which means that the author will receive a notification. Defaults to False.
        :type mention_author: bool, optional
        :param embed: An optional embed to include in the response message.
        :type embed: Embed | None, optional
        :param delete_after: If set, the response message will be deleted after the specified number of seconds.
        :type delete_after: float | None, optional
        :param silent: If True, the response will not notify the author of the original message. Defaults to False.
        :type silent: bool, optional
        :return: The sent Message object.
        :rtype: Message
        """
        message: Message = self.message.message_snowflake
        thread: Thread | None = message.thread

        if should_reply and not thread:
            return await message.reply(
                content=content,
                mention_author=mention_author,
                embed=embed,
                delete_after=delete_after,
                silent=silent,
            )
        elif thread:
            return await thread.send(
                content=content, embed=embed, delete_after=delete_after, silent=silent
            )
        else:
            return await message.channel.send(
                content=content, embed=embed, delete_after=delete_after, silent=silent
            )

    def __rate_limit_check(self) -> bool:
        """
        Checks if the user has exceeded the allowed number of messages in the last hour.

        :return: True if the user is within the allowed limit, False otherwise.
        :rtype: bool
        """

        author: User = self.message.message_snowflake.author
        author_id: int = author.id

        if author.id not in self._user_info.keys():
            self._user_info[author_id] = UserInfo(user_id=author_id, name=author.name)

        user: UserInfo = self._user_info.get(author_id)

        return user.update_message_stats(
            self.message.message_snowflake, self._bot_config
        )

    async def handle_response(self) -> None:
        """
        Handles the response based on the type of message received. It checks if the bot is in testing mode,
        performs a rate limit check, and then determines the appropriate response based on the channel type.
        """
        if self.__testing:
            await self.send_response(
                content="Testing mode is enabled. No response will be generated by the OpenAI API.",
                delete_after=60,
                silent=True,
            )
            return

        if not self.__rate_limit_check():
            await self.send_response(
                content="You have exceeded the allowed number of messages. Please try again later.",
                delete_after=60,
                silent=True,
            )

        channel: TextChannel | DMChannel | Thread | Any = self.message.channel

        match self.message.channel_type:
            case ChannelType.text:
                if not (
                    self.message.bot_user in self.message.mentions
                    and self._bot_config.can_message_channel(
                        channel=self.message.channel
                    )
                ):
                    return

                await self.__handle_reply_response()
            case ChannelType.private:
                await self.__handle_direct_response()
            case ChannelType.public_thread | ChannelType.private_thread:
                if not channel.owner or channel.owner != self.message.bot_user:
                    return
                await self.__handle_direct_response()
            case _:
                raise ValueError(
                    f"Unsupported ChannelType encountered: {self.message.channel_type}"
                )

    async def __handle_reply_response(self) -> None:
        """
        Handles a response which sends a message referencing the original message as a reply.

        This method handles the case where the bot is responding to the user in a public :class:`~discord.TextChannel`.

        :raises ValueError: If the channel type is not supported for reply responses.
        """
        if self.message.channel_type != ChannelType.text:
            raise ValueError(
                f"Unsupported ChannelType for reply response: {self.message.channel_type}"
            )

        message_history: list[ParsedMessage] = await self.message.get_history()

        if len(message_history) > 1:
            await self.__create_thread(referenced_message=message_history[0])
            await self.__generate_response(message_history, should_reply=False)
        else:
            await self.__generate_response(message_history, should_reply=True)

    async def __handle_direct_response(self) -> None:
        """
        Handles a response which sends a message without referencing the original message.

        This method handles the case where the bot is responding directly to the user in a :class:`~discord.DMChannel` or :class:`~discord.Thread`.
        """
        if self.message.channel_type not in (
            ChannelType.private,
            ChannelType.public_thread,
            ChannelType.private_thread,
        ):
            raise ValueError(
                f"Unsupported ChannelType for direct response: {self.message.channel_type}"
            )

        message_history: list[ParsedMessage] = await self.message.get_history()
        await self.__generate_response(
            message_history=message_history, should_reply=False
        )

    async def __generate_response(
        self,
        message_history: list[ParsedMessage],
        should_reply: bool,
    ) -> None:
        response_builder: ResponseBuilder = ResponseBuilder(
            config=self._ai_config,
            discord_messages=message_history,
            requestor=self.message.author,
        )

        response: Response = response_builder.get_response()
        embed: Embed | None = (
            Embed().set_image(url=response.gif) if response.gif else None
        )

        await self.send_response(
            content=response.get_text(),
            should_reply=should_reply,
            embed=embed,
        )

    async def __create_thread(self, referenced_message: ParsedMessage) -> Thread | None:
        if not referenced_message.from_this_bot:
            return None

        # TODO: Make an AI request to generate a thread name based on the message content
        thread_name = f"Follow-up Discussion with {self.message.author}"
        thread = await self.message.message_snowflake.create_thread(
            name=thread_name,
            auto_archive_duration=60,
            reason="Creating a thread for follow-up discussion.",
        )
        return thread
