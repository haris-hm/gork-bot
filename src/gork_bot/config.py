import random
import yaml
import os

from discord import User, TextChannel
from typing import Any
from abc import ABC, abstractmethod

from gork_bot.media_manager import CustomMediaStore


class Config(ABC):
    default_values: dict[str, Any] = {}

    def __init__(self, config_path: str):
        if not config_path.endswith(".yaml"):
            raise ValueError(
                "Configuration file must be a YAML file with a .yaml extension."
            )

        self.default_values = self.define_defaults()

        if not os.path.exists(config_path):
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(self.default_values, f, allow_unicode=True, indent=4)

        with open(config_path, "r", encoding="utf-8") as f:
            self.loaded_config: dict[str, Any] = yaml.safe_load(f)

    def get_config_value(self, key: str) -> Any:
        """Get a configuration value, falling back to the default if not set."""
        if key not in self.loaded_config or key not in self.default_values:
            raise KeyError(
                f"Configuration key '{key}' not found in loaded config or defaults."
            )

        return self.loaded_config.get(key, self.default_values.get(key))

    @abstractmethod
    def define_defaults(self) -> dict[str, Any]:
        """Define the default configuration values."""
        pass


class BotConfig(Config):
    def __init__(self, config_path: str):
        super().__init__(config_path)

        self.admins: set[int] = set(self.get_config_value("admins"))

        self.channel_whitelist: set[int] = set(
            self.get_config_value("channel_whitelist")
        )
        self.enable_whitelist: bool = self.get_config_value("enable_whitelist")

        self.allowed_messages_per_interval: int = self.get_config_value(
            "allowed_messages_per_interval"
        )
        self.timeout_interval_mins: int = self.get_config_value("timeout_interval_mins")

        self.can_respond_to_dm: bool = self.get_config_value("can_respond_to_dm")

    def define_defaults(self) -> dict[str, Any]:
        return {
            "admins": [],
            "channel_whitelist": [],
            "enable_whitelist": True,
            "allowed_messages_per_interval": 30,
            "timeout_interval_mins": 10,
            "can_respond_to_dm": True,
        }

    def is_admin(self, user: User) -> bool:
        return user.id in self.admins

    def can_message_channel(self, channel: TextChannel) -> bool:
        if self.enable_whitelist:
            return channel.id in self.channel_whitelist
        return True


class AIConfig(Config):
    def __init__(self, config_path: str):
        super().__init__(config_path)

        self.__identity: str = self.get_config_value("identity")
        self.__instructions: str = self.get_config_value("instructions")
        self.__random_additions: list[str] = self.get_config_value(
            "potential_additions"
        )
        self.__addition_chance: float = self.get_config_value("addition_chance")

        self.model: str = self.get_config_value("model")
        self.temperature: float = self.get_config_value("temperature")
        self.max_tokens: int = self.get_config_value("max_tokens")

        self.thread_name_generation_instructions: str = self.get_config_value(
            "thread_name_generation_instructions"
        )
        self.thread_history_limit: int = self.get_config_value("thread_history_limit")

        self.post_media: bool = self.get_config_value("post_media")
        self.__default_media: dict[str, float | str] = self.get_config_value(
            "default_media"
        )
        self.__custom_media: dict[str, float | str] = self.get_config_value(
            "custom_media"
        )
        self.__internet_media: dict[str, float | str] = self.get_config_value(
            "internet_media"
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

    def define_defaults(self) -> dict[str, Any]:
        return {
            "identity": "",
            "instructions": "",
            "potential_additions": [],
            "addition_chance": 0.2,
            "model": "gpt-4.1-mini",
            "temperature": 0.8,
            "max_tokens": 500,
            "thread_name_generation_instructions": "",
            "thread_history_limit": 10,
            "post_media": True,
            "default_media": {},
            "custom_media": {},
            "internet_media": {},
        }

    def add_to_instructions(self, instructions: str, addition: str) -> None:
        """Add a new instruction to the existing instructions."""
        if addition and isinstance(addition, str):
            return instructions + f" {addition.strip()}"
        else:
            return instructions

    def get_instructions(self) -> str:
        identity: str = self.__identity.strip()
        instructions: str = self.__instructions.strip()

        instructions = self.add_to_instructions(
            instructions, self.media_store.get_instructions()
        )

        if self.__random_additions and random.random() < self.__addition_chance:
            addition: str = random.choice(self.__random_additions)
            instructions = self.add_to_instructions(instructions, addition)

        return f"# Identity\n\n{identity}\n# Instructions\n\n{instructions}"
