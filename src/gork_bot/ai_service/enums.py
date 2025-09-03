from enum import Enum

from discord import ChannelType
from typing import Self


class GPT_Model(Enum):
    GPT_4_1_MINI = "gpt-4.1-mini"
    GPT_4_O_MINI = "gpt-4o-mini"
    GPT_4_1_NANO = "gpt-4.1-nano"
    GPT_5_MINI = "gpt-5-mini"


class MessageRole(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    DEVELOPER = "developer"
    TOOL = "tool"


class RequestReason(Enum):
    CHAT_COMPLETION = "chat_completion"
    THREAD_NAME_GENERATION = "thread_name_generation"
    IMAGE_GENERATION = "image_generation"
    VIDEO_GENERATION = "video_generation"
    AUDIO_GENERATION = "audio_generation"


class DiscordLocation(Enum):
    CHANNEL = "channel"
    DM = "dm"
    THREAD = "thread"
    UNKNOWN = "unknown"

    @classmethod
    def from_channel(cls, channel_type: ChannelType) -> Self:
        """
        Converts a channel type string to a DiscordLocation enum.
        """
        match channel_type:
            case ChannelType.private:
                return cls.DM
            case ChannelType.public_thread | ChannelType.private_thread:
                return cls.THREAD
            case ChannelType.text:
                return cls.CHANNEL
            case _:
                return cls.UNKNOWN
