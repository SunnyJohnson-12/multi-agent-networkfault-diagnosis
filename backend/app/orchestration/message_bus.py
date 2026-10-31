import asyncio
from typing import Dict, List, Set, Callable, Awaitable, Optional
from app.models.messages import AgentMessage, AgentRole, MessageType
from app.validation.validators import validate_agent_message


class MessageBus:
    """Asynchronous in-memory message bus routing protocol messages between agents

    and notifying live stream listeners.
    """

    def __init__(self, session_id: str):
        self.session_id: str = session_id
        self._message_log: List[AgentMessage] = []
        self._seen_message_ids: Set[str] = set()
        self._subscribers: Dict[str, List[Callable[[AgentMessage], Awaitable[None]]]] = {}
        self._stream_queues: List[asyncio.Queue] = []

    @property
    def message_count(self) -> int:
        return len(self._message_log)

    def get_messages(self) -> List[AgentMessage]:
        return list(self._message_log)

    def subscribe(self, agent_role: str, handler: Callable[[AgentMessage], Awaitable[None]]) -> None:
        if agent_role not in self._subscribers:
            self._subscribers[agent_role] = []
        self._subscribers[agent_role].append(handler)

    def register_stream_queue(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._stream_queues.append(q)
        # Pre-populate with historical messages for late joiners
        for msg in self._message_log:
            q.put_nowait(msg)
        return q

    def unregister_stream_queue(self, q: asyncio.Queue) -> None:
        if q in self._stream_queues:
            self._stream_queues.remove(q)

    async def publish(self, raw_or_model: AgentMessage) -> AgentMessage:
        if isinstance(raw_or_model, dict):
            msg = validate_agent_message(raw_or_model, self._seen_message_ids)
        else:
            msg = raw_or_model
            if msg.message_id in self._seen_message_ids:
                from app.validation.validators import ValidationErrorResponse
                raise ValidationErrorResponse(
                    error_code="DUPLICATE_MESSAGE_ID",
                    message=f"Duplicate message_id '{msg.message_id}' on session bus",
                    field="message_id",
                )

        self._seen_message_ids.add(msg.message_id)
        self._message_log.append(msg)

        # Notify active SSE stream listeners
        for q in list(self._stream_queues):
            try:
                q.put_nowait(msg)
            except Exception:
                pass

        # Route to target subscribers
        targets = [msg.target_agent.value]
        if msg.target_agent == AgentRole.BROADCAST:
            targets = list(self._subscribers.keys())

        for target in targets:
            handlers = self._subscribers.get(target, [])
            for handler in handlers:
                asyncio.create_task(self._safe_invoke(handler, msg))

        return msg

    async def _safe_invoke(self, handler: Callable[[AgentMessage], Awaitable[None]], msg: AgentMessage) -> None:
        try:
            await handler(msg)
        except Exception as e:
            # Error in handler execution should not crash the bus
            pass
