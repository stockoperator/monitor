from asyncio import Queue
from typing import Any


class EventQueueManager:
    def __init__(self):
        self._subscribers: set[Queue[Any]] = set()

    # += для подписки
    def __iadd__(self, queue: Queue[Any]):
        self._subscribers.add(queue)
        return self

    # -= для отписки
    def __isub__(self, queue: Queue[Any]):
        self._subscribers.discard(queue)
        return self

    # Вызов всех подписчиков
    def __call__(self, event: Any):
        for queue in self._subscribers:
            queue.put_nowait(event)
