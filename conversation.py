from collections import defaultdict
from typing import List, Dict
import time

class ConversationManager:
    def __init__(self, max_context_length: int = 10):
        self.conversations: Dict[int, List[Dict]] = defaultdict(list)
        self.max_context_length = max_context_length
        self.last_interaction: Dict[int, float] = defaultdict(float)

    def add_message(self, user_id: int, role: str, content: str, timestamp=None) -> None:
        """Add a message to the conversation history."""
        if timestamp is None:
            timestamp = time.time()

        self.conversations[user_id].append({
            "role": role,
            "content": content,
            "timestamp": timestamp
        })

        # Update last interaction time
        self.last_interaction[user_id] = timestamp

        # Trim conversation if it's too long
        if len(self.conversations[user_id]) > self.max_context_length:
            self.conversations[user_id] = self.conversations[user_id][-self.max_context_length:]

    def add_history(self, user_id: int, messages: List[Dict]) -> None:
        """Add multiple historical messages at once."""
        # Sort messages by timestamp to maintain chronological order
        sorted_messages = sorted(messages, key=lambda x: x.get('timestamp', 0))

        # Add each message while respecting max_context_length
        for msg in sorted_messages:
            self.add_message(
                user_id=user_id,
                role=msg.get('role', 'user'),
                content=msg.get('content', ''),
                timestamp=msg.get('timestamp', time.time())
            )

    def get_context(self, user_id: int) -> List[Dict]:
        """Get the conversation context for a user."""
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in self.conversations[user_id]
        ]

    def get_context_summary(self, user_id: int) -> str:
        """Get a readable summary of the conversation context."""
        if not self.conversations[user_id]:
            return "No conversation history."

        summary = []
        for msg in self.conversations[user_id]:
            role = "You" if msg["role"] == "user" else "Assistant"
            summary.append(f"{role}: {msg['content']}")

        return "\n".join(summary)

    def clear_context(self, user_id: int) -> None:
        """Clear the conversation context for a user."""
        self.conversations[user_id] = []
        self.last_interaction[user_id] = time.time()