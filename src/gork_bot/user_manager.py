from discord import Message, User
from datetime import datetime
from functools import wraps

from gork_bot.config import BotConfig


class UserInfo:
    def __init__(self, user_id: int, name: str):
        self.user_id: int = user_id
        self.name: str = name
        self.messages_in_last_hour: int = 0
        self.last_message_time: datetime | None = None

    def __repr__(self):
        return f"UserInfo(user_id={self.user_id}, name='{self.name}', messages_in_last_hour={self.messages_in_last_hour}, last_message_time={self.last_message_time})"

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


def rate_limit_check(method):
    @wraps(method)
    async def wrapper(self, message: Message, *args, **kwargs):
        author: User = message.author
        author_id: int = author.id

        if author.id not in self._user_info.keys():
            self._user_info[author_id] = UserInfo(user_id=author_id, name=author.name)

        user: UserInfo = self._user_info.get(author_id)

        if not user.update_message_stats(message, self._bot_config):
            await message.reply(
                content=f"Slow down, {author.mention}! You can only send {self._bot_config.allowed_messages_per_interval} messages every {self._bot_config.timeout_interval_mins} minute(s).",
                mention_author=False,
                silent=True,
                delete_after=60,
            )
            return
        else:
            async with message.channel.typing():
                return await method(self, message, *args, **kwargs)

    return wrapper
