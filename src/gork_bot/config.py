import json
import random

from discord import User, TextChannel
from typing import Any

from gork_bot.media_manager import CustomMediaStore


class BotConfig:
    def __init__(self, config_path: str):
        with open(config_path, "r", encoding="utf-8") as f:
            config: dict[str, Any] = json.load(f)

            self.admins: list[int] = set(config.get("admins", []))

            self.channel_whitelist: list[int] = set(config.get("channel_whitelist", []))
            self.enable_whitelist: bool = config.get("enable_whitelist", False)

            self.allowed_messages_per_interval: int = config.get(
                "allowed_messages_per_interval", 30
            )
            self.timeout_interval_mins: int = config.get("timeout_interval_mins", 10)

            self.stream_output: bool = config.get("stream_output", True)
            self.stream_edit_interval_secs: float = config.get(
                "stream_edit_interval_secs", 0.5
            )

    def is_admin(self, user: User) -> bool:
        return user.id in self.admins

    def can_message_channel(self, channel: TextChannel) -> bool:
        if self.enable_whitelist:
            return channel.id in self.channel_whitelist
        return True


class AIConfig:
    def __init__(self, config_path: str):
        with open(config_path, "r", encoding="utf-8") as f:
            config: dict[str, Any] = json.load(f)

            self.__instructions: str = config.get("instructions", "")
            self.__random_additions: list[str] = config.get("potential_additions", [])
            self.__addition_chance: float = config.get("addition_chance", 0.2)

            self.model: str = config.get("model", "gpt-4.1-mini")
            self.temperature: float = config.get("temperature", 0.8)
            self.max_tokens: int = config.get("max_tokens", 500)

            self.post_media: bool = config.get("post_media", True)
            self.__default_media: dict[str, float | str] = config.get(
                "default_media", {}
            )
            self.__custom_media: dict[str, float | str] = config.get("custom_media", {})
            self.__internet_media: dict[str, float | str] = config.get(
                "internet_media", {}
            )
            self.media_store: CustomMediaStore = CustomMediaStore(
                default_media=self.__default_media,
                custom_media=self.__custom_media,
                internet_media=self.__internet_media,
            )

            if not (0 <= self.__addition_chance <= 1):
                raise ValueError("Addition chance must be between 0 and 1.")

            if not (0 <= self.temperature <= 1):
                raise ValueError("Temperature must be between 0 and 1.")

            if self.max_tokens <= 0:
                raise ValueError("Max tokens must be a positive integer.")

    def add_to_instructions(self, instructions: str, addition: str) -> None:
        """Add a new instruction to the existing instructions."""
        if addition and isinstance(addition, str):
            return instructions + f" {addition.strip()}"
        else:
            return instructions

    def get_instructions(self) -> str:
        instructions: str = self.__instructions.strip()

        instructions = self.add_to_instructions(
            instructions, self.media_store.get_instructions()
        )

        if self.__random_additions and random.random() < self.__addition_chance:
            addition: str = random.choice(self.__random_additions)
            instructions = self.add_to_instructions(instructions, addition)

        return instructions
