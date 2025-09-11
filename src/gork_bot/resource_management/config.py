import os
import random
import yaml

from abc import ABC, abstractmethod
from typing import Any


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


class BotConfigV2(Config):
    def __init__(self, config_path: str):
        super().__init__(config_path)

        self.presence_message_path: str = self.get_config_value("presence_message_path")
        self.presence_message_interval_mins: int = self.get_config_value(
            "presence_message_interval_mins"
        )

        self.model: str = self.get_config_value("model")
        self.temperature: float = self.get_config_value("temperature")
        self.max_tokens: int = self.get_config_value("max_tokens")

        self.identity: str = self.get_config_value("identity")
        self.instructions: str = self.get_config_value("instructions")

        self.thread_history_limit: int = self.get_config_value("thread_history_limit")
        self.thread_name_generation_identity: str = self.get_config_value(
            "thread_name_generation_identity"
        )
        self.thread_name_generation_instructions: str = self.get_config_value(
            "thread_name_generation_instructions"
        )

        self.__default_media: dict[str, float | str] = self.get_config_value(
            "default_media"
        )
        self.__custom_media: dict[str, float | str] = self.get_config_value(
            "custom_media"
        )
        self.__internet_media: dict[str, float | str] = self.get_config_value(
            "internet_media"
        )

        if self.presence_message_interval_mins <= 0:
            raise ValueError("Presence message interval must be a positive integer.")

        if not (0 <= self.temperature <= 1):
            raise ValueError("Temperature must be between 0 and 1.")

        if self.max_tokens <= 0:
            raise ValueError("Max tokens must be a positive integer.")

        if self.thread_history_limit <= 0:
            raise ValueError("Thread history limit must be a positive integer.")

    def define_defaults(self):
        return {
            "presence_message_path": "resources/default_presence_message_storage.json",
            "presence_message_interval_mins": 60,
            "model": "gpt-4.1-mini",
            "temperature": 0.8,
            "max_tokens": 1000,
            "identity": "",
            "instructions": "",
            "thread_history_limit": 10,
            "thread_name_generation_identity": "",
            "thread_name_generation_instructions": "",
            "default_media": {},
            "custom_media": {},
            "internet_media": {},
        }

    def get_instructions(self, tags: set[str]) -> str:
        """
        Returns the custom media instructions.

        :return: A string containing the custom media instructions.
        """
        default_weight = max(
            0.0, 1.0 - (self.custom_media_weight + self.internet_media_weight)
        )

        options = [
            self.default_media_instructions,
            f"{self.custom_media_instructions}: {', '.join(sorted(tags))}",
            self.internet_media_instructions,
        ]
        weights = [
            default_weight,
            self.custom_media_weight,
            self.internet_media_weight,
        ]

        return random.choices(options, weights=weights, k=1)[0].strip()
