from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from collections import deque
import os
import select
from threading import Thread, Event

READABLE_EVENTS = select.POLLIN | select.POLLPRI
WRITEABLE_EVENTS = select.POLLOUT
ERROR_EVENTS = select.POLLERR | select.POLLHUP

@dataclass
class Write:
    """Data in a write queue."""

    data: bytes
    position: int = 0
    done_event: asyncio.Event = field(default_factory=asyncio.Event)



class Poller(Thread):
    """A thread which reads from file descriptors and posts read data to a queue."""

    def __init__(self) -> None:
        super().__init__()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._poll = select.poll()
        self._read_queues: dict[int, asyncio.Queue[bytes | None]] = {}
        self._write_queues: dict[int, deque[Write]] = {}
        self._exit_event = Event()

    def add_file(self, file_descriptor: int) -> asyncio.Queue:
        """Add a file descriptor to the poller.

        Args:
            file_descriptor: File descriptor.

        Returns:
            Async queue.
        """
        self._poll.register(
            file_descriptor, READABLE_EVENTS | WRITEABLE_EVENTS | ERROR_EVENTS
        )
        queue = self._read_queues[file_descriptor] = asyncio.Queue()
        return queue

    def remove_file(self, file_descriptor: int) -> None:
        """Remove a file descriptor from the poller.

        Args:
            file_descriptor: File descriptor.
        """
        self._read_queues.pop(file_descriptor, None)
        self._write_queues.pop(file_descriptor, None)

    async def write(self, file_descriptor: int, data: bytes) -> None:
        """Write data to a file descriptor.

        Args:
            file_descriptor: File descriptor.
            data: Data to write.
        """
        if file_descriptor not in self._write_queues:
            self._write_queues[file_descriptor] = deque()
        new_write = Write(data)
        self._write_queues[file_descriptor].append(new_write)
        self._poll.register(
            file_descriptor, READABLE_EVENTS | WRITEABLE_EVENTS | ERROR_EVENTS
        )
        await new_write.done_event.wait()

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Set the asyncio loop.

        Args:
            loop: Async loop.
        """
        self._loop = loop

    def run(self) -> None:
        """Run the Poller thread."""
        readable_events = READABLE_EVENTS
        writeable_events = WRITEABLE_EVENTS
        error_events = ERROR_EVENTS
        loop = self._loop
        assert loop is not None
        while not self._exit_event.is_set():
            poll_result = self._poll.poll(1000)
            for file_descriptor, event_mask in poll_result:
                queue = self._read_queues.get(file_descriptor, None)
                if queue is not None:
                    if event_mask & readable_events:
                        data = os.read(file_descriptor, 1024 * 32)
                        loop.call_soon_threadsafe(queue.put_nowait, data)

                    if event_mask & writeable_events:
                        write_queue = self._write_queues.get(file_descriptor, None)
                        if write_queue:
                            write = write_queue[0]
                            bytes_written = os.write(
                                file_descriptor, write.data[write.position :]
                            )
                            if bytes_written == len(write.data):
                                write_queue.popleft()
                                loop.call_soon_threadsafe(write.done_event.set)
                            else:
                                write.position += bytes_written

                    if event_mask & error_events:
                        loop.call_soon_threadsafe(queue.put_nowait, None)
                        self._read_queues.pop(file_descriptor, None)

    def exit(self) -> None:
        """Exit and block until finished."""
        for queue in self._read_queues.values():
            queue.put_nowait(None)
        self._exit_event.set()
        self.join()
        self._read_queues.clear()
        self._write_queues.clear()
