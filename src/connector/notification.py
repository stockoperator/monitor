from aiohttp import ClientSession
from connector.config import NTFY_TOPIC

NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"


class Notification:
    def __init__(self, session: ClientSession):
        self.session = session

    async def send(
        self,
        message: str,
        title: str = "",
        priority: str = "",
        tags: str = "",
    ) -> None:
        headers = {
            "Title": title,
            "Priority": priority,
            "Tags": tags,
        }

        resp = await self.session.post(NTFY_URL, data=message.encode("utf-8"), headers=headers)
        resp.raise_for_status()
