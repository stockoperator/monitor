from aiohttp import ClientSession
import os


class Notification:
    def __init__(self, session: ClientSession, topic: str = "") -> None:
        if not topic:
            topic = os.getenv("NTFY_TOPIC", "")
        if not topic:
            raise ValueError("topic is not set")
        self.url = f"https://ntfy.sh/{topic}"
        self.session = session

    async def send(
        self,
        message: str,
        title: str = "",
        priority: str = "",
        tags: str = "",
        click_url: str = "",
    ) -> None:
        headers: dict[str, str] = {}
        if title:
            headers["Title"] = title
        if priority:
            headers["Priority"] = priority
        if tags:
            headers["Tags"] = tags
        if click_url:
            headers["Click"] = click_url

        async with self.session.post(self.url, data=message.encode("utf-8"), headers=headers) as resp:
            resp.raise_for_status()
