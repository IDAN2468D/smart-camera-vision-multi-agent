import json
import queue
import logging
import threading
from typing import Generator, Set

logger = logging.getLogger(__name__)

class SSEService:
    """Thread-safe Server-Sent Events (SSE) event bus for pushing real-time updates to connected clients."""

    def __init__(self):
        self._subscribers: Set[queue.Queue] = set()
        self._lock = threading.Lock()

    def register(self) -> queue.Queue:
        """Register a new client listener queue."""
        q = queue.Queue(maxsize=50)
        with self._lock:
            self._subscribers.add(q)
            logger.info(f"SSE client connected. Active subscribers: {len(self._subscribers)}")
        return q

    def unregister(self, q: queue.Queue):
        """Remove a disconnected client queue."""
        with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)
                logger.info(f"SSE client disconnected. Active subscribers: {len(self._subscribers)}")

    def publish(self, event_type: str, data: dict):
        """Broadcast an event payload to all currently connected SSE clients.
        
        Args:
            event_type: Name of the event (e.g. 'detection', 'status', 'heartbeat').
            data: Dictionary payload to serialize as JSON.
        """
        payload = (
            f"event: {event_type}\n"
            f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
        )
        with self._lock:
            dead_queues = []
            for q in self._subscribers:
                try:
                    q.put_nowait(payload)
                except queue.Full:
                    # Client is slow/frozen, drop or mark for removal
                    dead_queues.append(q)
            for dq in dead_queues:
                self._subscribers.remove(dq)

    def event_stream(self) -> Generator[str, None, None]:
        """Generator yielding SSE formatted strings for Flask Response streaming."""
        client_queue = self.register()
        # Yield initial connection confirmation
        initial_event = (
            "event: connected\n"
            'data: {"status": "connected", "message": "Vision SSE stream active"}\n\n'
        )
        yield initial_event

        try:
            while True:
                try:
                    # Wait up to 15 seconds for a message
                    message = client_queue.get(timeout=15.0)
                    yield message
                except queue.Empty:
                    # Send periodic keep-alive heartbeat comment to prevent proxy timeouts
                    yield ": ping\n\n"
        except GeneratorExit:
            logger.debug("SSE client connection terminated.")
        finally:
            self.unregister(client_queue)

# Singleton service instance
sse_service = SSEService()
