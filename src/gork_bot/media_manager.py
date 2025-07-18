import json

from collections import defaultdict


class CustomMediaStore:
    """
    A class to manage custom media, such as GIFs, images, and videos, with tagging functionality.
    It allows for the retrieval of media based on keywords and provides instructions for using the media.
    """

    def __init__(self, path: str, instructions: str = ""):
        self.instructions = instructions.strip()

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

            self.gifs: defaultdict[str, list[str]] = self.build_tag_index(
                data.get("gifs", {})
            )

    def build_tag_index(
        self, gifs: list[dict[str, str | list[str]]]
    ) -> defaultdict[str, list[str]]:
        """
        Builds a tag index from the provided GIFs.
        Each GIF is expected to have a 'tags' field (list of strings) and a 'url' field (string).
        Returns a defaultdict where keys are tags and values are lists of URLs.

        :param gifs: List of GIF dictionaries.
        :return: A defaultdict mapping tags to lists of URLs.
        """

        tag_index: defaultdict[str, list[str]] = defaultdict(list)

        for gif in gifs:
            tags: list[str] = gif.get("tags", [])
            url: str = gif.get("url", "")

            if not tags or not url:
                continue

            for tag in tags:
                tag_index[tag].append(url)

        return tag_index

    def get_gifs(self) -> defaultdict[str, list[str]]:
        """
        Returns the dictionary of GIFs.
        """
        return self.gifs

    def get_gif(self, keyword: str) -> list[str]:
        """
        Returns the GIFs associated with a specific keyword.
        If the keyword does not exist, returns an empty list.

        :param keyword: The keyword to search for.
        :return: A list of GIF URLs associated with the keyword, or an empty list if not found.
        """

        return self.gifs.get(keyword, [])

    def get_instructions(self) -> str:
        """
        Returns the custom media instructions.

        :return: A string containing the custom media instructions.
        """
        custom_instructions = f"{self.instructions}: [{', '.join(self.gifs.keys())}]."
        return custom_instructions.strip()
