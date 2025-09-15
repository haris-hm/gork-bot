import json
import random

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
        should_request_additions: bool,
        addition_chance: float,
        should_post_media: bool = True,
        connection: Connection | None = None,
    ):
        self._connection: Connection | None = connection
        self.guild_id: int = guild_id
        self.channel_allowlist_enabled: bool = channel_allowlist_enabled
        self.timeout_interval_mins: int = timeout_interval_mins
        self.allowed_messages_per_interval: int = allowed_messages_per_interval
        self.channel_allowlist: set[int] = set(channel_allowlist)
        self.should_request_additions: bool = should_request_additions
        self.addition_chance: float = addition_chance
        self.should_post_media: bool = should_post_media

    @classmethod
    def get_by_id(
        cls, guild_id: int, connection: Connection | None = None
    ) -> Self | None:
        query: str = """
            SELECT guild_id, channel_allowlist_enabled, 
                timeout_interval_mins, allowed_messages_per_interval, 
                channel_allowlist, should_request_additions, addition_chance,
                should_post_media
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
                should_request_additions=guild_data[5],
                addition_chance=guild_data[6],
                should_post_media=guild_data[7],
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
        should_request_additions: bool = True,
        addition_chance: float = 0.2,
        should_post_media: bool = True,
        connection: Connection | None = None,
    ) -> Self:
        query: str = """
            INSERT INTO guilds 
            (guild_id, channel_allowlist_enabled, 
                timeout_interval_mins, allowed_messages_per_interval, 
                channel_allowlist, should_request_additions, addition_chance,
                should_post_media) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        run_query(
            query=query,
            params=(
                guild_id,
                channel_allowlist_enabled,
                timeout_interval_mins,
                allowed_messages_per_interval,
                should_request_additions,
                addition_chance,
                should_post_media,
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
            should_request_additions=should_request_additions,
            addition_chance=addition_chance,
            should_post_media=should_post_media,
            connection=connection,
        )

    @classmethod
    def get_all_guild_ids(cls, connection: Connection | None = None) -> list[int]:
        query: str = """
            SELECT guild_id
            FROM guilds
        """
        result: list[tuple[Any]] = run_query(query=query, connection=connection)
        return [str(row[0]) for row in result]

    def channel_allowed(self, channel_id: int) -> bool:
        if not self.channel_allowlist_enabled:
            return True
        return channel_id in self.channel_allowlist

    def get_prompt_addition(self) -> str:
        query: str = """
            SELECT addition_text
            FROM potential_additions
            WHERE guild_id = %s
        """

        result: list[tuple[str]] = run_query(
            query=query, params=(self.guild_id,), connection=self._connection
        )

        if result:
            additions: list[str] = [row[0] for row in result]
            return random.choice(additions)

        return ""

    def add_prompt_addition(self, addition_text: str) -> None:
        query: str = """
            INSERT INTO potential_additions
            (guild_id, addition_text)
            VALUES (%s, %s)
        """

        run_query(
            query=query,
            params=(self.guild_id, addition_text),
            connection=self._connection,
        )

    def remove_prompt_addition(self, addition_text: str) -> bool:
        check_query: str = """
            SELECT 1
            FROM potential_additions
            WHERE guild_id = %s AND addition_text = %s
        """

        check_result: list[tuple[Any]] = run_query(
            query=check_query,
            params=(self.guild_id, addition_text),
            connection=self._connection,
        )

        if not check_result:
            return False

        remove_query: str = """
            DELETE FROM potential_additions
            WHERE guild_id = %s AND addition_text = %s
        """

        run_query(
            query=remove_query,
            params=(self.guild_id, addition_text),
            connection=self._connection,
        )

        return True

    def get_all_prompt_additions(self) -> list[str]:
        query: str = """
            SELECT addition_text
            FROM potential_additions
            WHERE guild_id = %s
        """

        result: list[tuple[str]] = run_query(
            query=query, params=(self.guild_id,), connection=self._connection
        )

        return [row[0] for row in result] if result else []


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
        self,
        user_id: int,
        messages_in_last_hour: int,
        last_message_time: datetime,
        increment: bool = True,
    ) -> None:
        query: str = ""

        if increment:
            query = """
                UPDATE users
                SET messages_in_last_hour = messages_in_last_hour + %s,
                    last_message_time = %s,
                    lifetime_messages = lifetime_messages + 1
                WHERE user_id = %s
                """
        else:
            query = """
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


class GorkMedia:
    def __init__(
        self, media: dict[str, list[str]], connection: Connection | None = None
    ):
        self._connection: Connection | None = connection
        self.media: dict[str, list[str]] = media

    @classmethod
    def get_from_guild_id(
        cls, guild_id: int, connection: Connection | None = None
    ) -> Self | None:
        query: str = """
            SELECT link, tag_name
            FROM custom_media cm
                JOIN media_tags mt
                    ON cm.media_id = mt.media_id
                    AND cm.guild_id = mt.guild_id
                JOIN tags
                    ON mt.tag_id = tags.tag_id
            WHERE cm.guild_id = %s
        """

        result: list[tuple[Any]] = run_query(
            query=query, params=(guild_id,), connection=connection
        )

        if result:
            media: dict[str, list[str]] = {}
            for media_link, tag_name in result:
                if tag_name not in media:
                    media[tag_name] = []
                media[tag_name].append(media_link)
            return cls(media=media)

        return None

    def get_media_tags(self) -> set[str]:
        return set(self.media.keys())

    def get_gif(self, tag: str) -> list[str]:
        return self.media.get(tag, [])


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
        self.media: GorkMedia = GorkMedia.get_from_guild_id(
            guild_id=guild_id, connection=connection
        )
