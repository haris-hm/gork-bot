import json

from datetime import datetime
from typing import Self, Any
from pymysql.connections import Connection

from gork_bot.db_service.connection import run_query


class GorkGuild:
    def __init__(
        self,
        guild_id: int,
        channel_allowlist_enabled: bool,
        timeout_interval_mins: int,
        allowed_messages_per_interval: int,
        channel_allowlist: list[int],
        connection: Connection | None = None,
    ):
        self.connection: Connection | None = connection
        self.guild_id: int = guild_id
        self.channel_allowlist_enabled: bool = channel_allowlist_enabled
        self.timeout_interval_mins: int = timeout_interval_mins
        self.allowed_messages_per_interval: int = allowed_messages_per_interval
        self.channel_allowlist: set[int] = set(channel_allowlist)

    @classmethod
    def get_by_id(
        cls, guild_id: int, connection: Connection | None = None
    ) -> Self | None:
        query: str = """
            SELECT guild_id, channel_allowlist_enabled, 
                timeout_interval_mins, allowed_messages_per_interval, 
                channel_allowlist
            FROM guilds
            WHERE guild_id = %s
        """

        result: list[tuple[Any]] = run_query(
            query=query, params=(guild_id,), connection=connection
        )
        if result:
            guild_data: tuple[Any] = result[0]
            return cls(
                guild_id=guild_data[0],
                channel_allowlist_enabled=guild_data[1],
                timeout_interval_mins=guild_data[2],
                allowed_messages_per_interval=guild_data[3],
                channel_allowlist=json.loads(guild_data[4]),
                connection=connection,
            )

        return GorkGuild.create(guild_id=guild_id)

    @classmethod
    def create(
        cls,
        guild_id: int,
        channel_allowlist_enabled: bool = True,
        timeout_interval_mins: int = 10,
        allowed_messages_per_interval: int = 30,
        connection: Connection | None = None,
    ) -> Self:
        query: str = """
            INSERT INTO guilds 
            (guild_id, channel_allowlist_enabled, 
                timeout_interval_mins, allowed_messages_per_interval, 
                channel_allowlist) 
            VALUES (%s, %s, %s, %s, %s)
        """
        run_query(
            query=query,
            params=(
                guild_id,
                channel_allowlist_enabled,
                timeout_interval_mins,
                allowed_messages_per_interval,
                json.dumps([]),
            ),
            connection=connection,
        )
        return cls(
            guild_id=guild_id,
            channel_allowlist_enabled=channel_allowlist_enabled,
            timeout_interval_mins=timeout_interval_mins,
            allowed_messages_per_interval=allowed_messages_per_interval,
            channel_allowlist=[],
            connection=connection,
        )

    def channel_allowed(self, channel_id: int) -> bool:
        if not self.channel_allowlist_enabled:
            return True
        return channel_id in self.channel_allowlist


class GorkUser:
    def __init__(
        self,
        user_id: int,
        messages_in_last_hour: int,
        last_message_time: datetime | None,
        lifetime_messages: int,
        permissions: dict[str, bool],
        connection: Connection | None = None,
    ):
        self._connection: Connection | None = connection
        self.user_id: int = user_id
        self.messages_in_last_hour: int = messages_in_last_hour
        self.last_message_time: datetime = last_message_time
        self.lifetime_messages: int = lifetime_messages
        self.permissions: dict[str, bool] = permissions

    @staticmethod
    def default_user_permissions() -> dict[str, bool]:
        return {
            "admin": False,
            "bypass_rate_limit": False,
            "send_messages": True,
        }

    @classmethod
    def get_by_id(
        cls, user_id: int, guild_id: int, connection: Connection | None = None
    ) -> Self | None:
        query: str = """
        SELECT users.user_id, messages_in_last_hour,
            last_message_time, lifetime_messages, permissions
        FROM users JOIN user_permissions perms
            ON users.user_id = perms.user_id
        WHERE users.user_id = %s AND perms.guild_id = %s 
        """

        result: list[tuple[Any]] = run_query(query=query, params=(user_id, guild_id))
        if result:
            user_data: tuple[Any] = result[0]
            return cls(
                user_id=user_data[0],
                messages_in_last_hour=user_data[1],
                last_message_time=user_data[2],
                lifetime_messages=user_data[3],
                permissions=json.loads(user_data[4]),
                connection=connection,
            )

        return GorkUser.create(
            user_id=user_id, guild_id=guild_id, connection=connection
        )

    @classmethod
    def create(
        cls, user_id: int, guild_id: int, connection: Connection | None = None
    ) -> Self:
        user_creation_query: str = """
            INSERT INTO users 
            (user_id) 
            VALUES (%s)
        """
        permission_creation_query: str = """
            INSERT INTO user_permissions
            (user_id, guild_id, permissions)
            VALUES (%s, %s, %s)
        """
        default_permissions: dict[str, bool] = GorkUser.default_user_permissions()

        run_query(query=user_creation_query, params=(user_id,), connection=connection)
        run_query(
            query=permission_creation_query,
            params=(user_id, guild_id, json.dumps(default_permissions)),
            connection=connection,
        )

        return cls(
            user_id=user_id,
            messages_in_last_hour=0,
            last_message_time=datetime.now(),
            lifetime_messages=0,
            permissions=default_permissions,
            connection=connection,
        )

    def update_messages(
        self, user_id: int, messages_in_last_hour: int, last_message_time: datetime
    ) -> None:
        query: str = """
            UPDATE users 
            SET messages_in_last_hour = %s, 
                last_message_time = %s, 
                lifetime_messages = lifetime_messages + 1
            WHERE user_id = %s
        """
        run_query(
            query=query,
            params=(
                messages_in_last_hour,
                last_message_time,
                user_id,
            ),
            connection=self._connection,
        )


class GorkMessageContext:
    def __init__(
        self, user_id: int, guild_id: int, connection: Connection | None = None
    ):
        self.guild: GorkGuild = GorkGuild.get_by_id(
            guild_id=guild_id, connection=connection
        )
        self.user: GorkUser = GorkUser.get_by_id(
            user_id=user_id, guild_id=guild_id, connection=connection
        )
