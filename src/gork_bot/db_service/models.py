from datetime import datetime
from typing import Self

from gork_bot.db_service.connection import run_query


class GorkGuild:
    def __init__(self, guild_id: int):
        pass


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
        query = "SELECT * FROM users WHERE discord_id = %s"
        result = run_query(query, (discord_id,))
        if result:
            user_data = result[0]
            return cls(
                discord_id=user_data["discord_id"],
                username=user_data["name"],
                messages_in_last_hour=user_data["messages_in_last_hour"],
                last_message_time=user_data["last_message_time"],
            )
        return None


class GorkChannel:
    def __init__(self):
        pass


# Guilds
def get_guild_by_id(guild_id: int) -> dict | None:
    query = "SELECT * FROM guilds WHERE guild_id = %s"
    result = run_query(query, (guild_id,))
    return result[0] if result else None


def create_guild(
    guild_id: int,
    guild_name: str,
    channel_allowlist_enabled: bool = True,
    timeout_interval_mins: int = 10,
) -> tuple[int, str, bool, int]:
    query = """
        INSERT INTO guilds (guild_id, guild_name, channel_allowlist_enabled, timeout_interval_mins) 
        VALUES (%s, %s, %s, %s)
    """
    run_query(
        query, (guild_id, guild_name, channel_allowlist_enabled, timeout_interval_mins)
    )
    return (guild_id, guild_name, channel_allowlist_enabled, timeout_interval_mins)


# Users
def get_user_by_id(
    discord_id: int,
) -> tuple[int, str, int | None, datetime | None] | None:
    query = "SELECT * FROM users WHERE discord_id = %s"
    result = run_query(query, (discord_id,))
    return result[0] if result else None


def create_user(discord_id: int, username: str) -> tuple[int, str, None, None]:
    query = "INSERT INTO users (discord_id, name) VALUES (%s, %s)"
    run_query(query, (discord_id, username))
    return (discord_id, username, None, None)


def update_user_messages(
    discord_id: int, messages_in_last_hour: int, last_message_time: datetime
) -> None:
    query = """
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
