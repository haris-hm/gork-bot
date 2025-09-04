from datetime import datetime
from typing import Self, Any

from gork_bot.db_service.connection import run_query


class GorkGuild:
    def __init__(
        self,
        guild_id: int,
        guild_name: str,
        channel_allowlist_enabled: bool,
        timeout_interval_mins: int,
        allowed_messages_per_interval: int,
    ):
        self.guild_id: int = guild_id
        self.guild_name: str = guild_name
        self.channel_allowlist_enabled: bool = channel_allowlist_enabled
        self.timeout_interval_mins: int = timeout_interval_mins
        self.allowed_messages_per_interval: int = allowed_messages_per_interval

    @classmethod
    def get_by_id(cls, guild_id: int) -> Self | None:
        query: str = "SELECT * FROM guilds WHERE guild_id = %s"
        result: list[tuple[Any]] = run_query(query, (guild_id,))
        if result:
            guild_data: tuple[Any] = result[0]
            return cls(
                guild_id=guild_data[0],
                guild_name=guild_data[1],
                channel_allowlist_enabled=guild_data[2],
                timeout_interval_mins=guild_data[3],
                allowed_messages_per_interval=guild_data[4],
            )

        return None

    @classmethod
    def create(
        cls,
        guild_id: int,
        guild_name: str,
        channel_allowlist_enabled: bool = True,
        timeout_interval_mins: int = 10,
        allowed_messages_per_interval: int = 30,
    ) -> Self:
        query: str = """
            INSERT INTO guilds (guild_id, guild_name, channel_allowlist_enabled, timeout_interval_mins, allowed_messages_per_interval) 
            VALUES (%s, %s, %s, %s, %s)
        """
        run_query(
            query,
            (
                guild_id,
                guild_name,
                channel_allowlist_enabled,
                timeout_interval_mins,
                allowed_messages_per_interval,
            ),
        )
        return cls(
            guild_id=guild_id,
            guild_name=guild_name,
            channel_allowlist_enabled=channel_allowlist_enabled,
            timeout_interval_mins=timeout_interval_mins,
            allowed_messages_per_interval=allowed_messages_per_interval,
        )

    def channel_allowed(self, channel_id: int) -> bool:
        if not self.channel_allowlist_enabled:
            return True

        query: str = (
            "SELECT 1 FROM channel_allowlist WHERE guild_id = %s AND channel_id = %s"
        )
        result: list[tuple[Any]] = run_query(query, (self.guild_id, channel_id))
        return bool(result)


class GorkUser:
    def __init__(
        self,
        discord_id: int,
        username: str,
        messages_in_last_hour: int,
        last_message_time: datetime | None,
    ):
        self.discord_id: int = discord_id
        self.username: str = username
        self.messages_in_last_hour: int = messages_in_last_hour
        self.last_message_time: datetime | None = last_message_time

    @classmethod
    def get_by_id(cls, discord_id: int) -> Self | None:
        query: str = "SELECT * FROM users WHERE discord_id = %s"
        result: list[tuple[Any]] = run_query(query, (discord_id,))
        if result:
            user_data: tuple[Any] = result[0]
            return cls(
                discord_id=user_data[0],
                username=user_data[1],
                messages_in_last_hour=user_data[2],
                last_message_time=user_data[3],
            )
        return None

    @classmethod
    def create(cls, discord_id: int, username: str) -> Self:
        query: str = """
            INSERT INTO users 
            (discord_id, name, messages_in_last_hour, last_message_time) 
            VALUES (%s, %s, %s, %s)
        """
        message_datestamp: datetime = datetime.now()
        run_query(query, (discord_id, username, 1, message_datestamp))
        return cls(
            discord_id=discord_id,
            username=username,
            messages_in_last_hour=1,
            last_message_time=message_datestamp,
        )

    @classmethod
    def update_messages(
        cls, discord_id: int, messages_in_last_hour: int, last_message_time: datetime
    ) -> None:
        query: str = """
            UPDATE users 
            SET messages_in_last_hour = %s, last_message_time = %s
            WHERE discord_id = %s
        """
        run_query(
            query,
            (
                messages_in_last_hour,
                last_message_time,
                discord_id,
            ),
        )
