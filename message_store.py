from collections import deque


class MessageStore:
    def __init__(self, callback, max_size) -> None:
        self._callback = callback
        self._deque = deque(maxlen=max_size)

    async def append(self, item):
        self._deque.append(item)
        await self._callback(self._deque)
