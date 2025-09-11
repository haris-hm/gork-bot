import json
import random

from discord import Activity, ActivityType
from typing import Any


class PresenceMessageStore:
    """
    A class to manage presence messages for the bot.
    It allows for the retrieval of a random presence message.
    """

    def __init__(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            self.presence_messages = json.load(f)

    def get_random_presence_message(self) -> Activity:
        """
        Returns a random presence message from the store.

        :return: The Activity object representing the presence message.
        """
        random_message: dict[str, Any] = random.choice(
            self.presence_messages["messages"]
        )
        activity: Activity = Activity(
            type=ActivityType[random_message.get("type", "listening")],
            name=random_message.get("name", "Gorkin' it"),
        )

        if "url" in random_message.keys():
            activity.url = random_message.get("url")

        if "state" in random_message.keys():
            activity.state = random_message.get("state")

        if "platform" in random_message.keys():
            activity.platform = random_message.get("platform")

        return activity
