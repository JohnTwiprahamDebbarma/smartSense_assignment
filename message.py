"""
Message class for communication between agents via the event bus.
"""

import uuid
import time
from typing import Dict, Any, Optional, List
from enum import Enum, auto
from dataclasses import dataclass, field


class MessageType(Enum):
    """Enum of message types for inter-agent communication."""
    
    # Audio and transcription related messages
    AUDIO_CAPTURED = auto()
    TRANSCRIPTION_COMPLETE = auto()
    
    # Semantic analysis related messages
    SEMANTIC_ANALYSIS_COMPLETE = auto()
    INTENT_CLASSIFIED = auto()
    THEME_DETECTED = auto()
    
    # Decision and action item related messages
    DECISIONS_EXTRACTED = auto()
    ACTION_ITEMS_EXTRACTED = auto()
    RISKS_EXTRACTED = auto()
    SUMMARY_GENERATED = auto()
    
    # Task management related messages
    TASK_CREATED = auto()
    TASK_UPDATED = auto()
    REMINDER_SENT = auto()
    ESCALATION_TRIGGERED = auto()
    
    # System messages
    ERROR = auto()
    LOG = auto()
    SYSTEM_COMMAND = auto()
    CONFIG_UPDATED = auto()
    
    # Memory related messages
    MEMORY_STORED = auto()
    MEMORY_RETRIEVED = auto()
    CONTEXT_UPDATED = auto()


@dataclass
class Message:
    """
    Message object for communication between agents.
    
    Contains metadata about the message as well as the payload.
    """
    
    # Message type from the MessageType enum
    type: MessageType
    
    # The main content/payload of the message
    content: Dict[str, Any]
    
    # Metadata fields
    sender: Optional[str] = None  # ID of the sending agent
    recipient: Optional[str] = None  # ID of intended recipient (if any)
    timestamp: float = field(default_factory=time.time)  # When the message was created
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))  # Unique ID
    
    # Fields for message threading and context
    parent_id: Optional[str] = None  # ID of the parent message if this is a reply
    context_id: Optional[str] = None  # ID for grouping related messages (e.g., meeting ID)
    thread_id: Optional[str] = None  # Thread ID for conversation tracking
    
    # Optional fields
    priority: int = 0  # Higher number = higher priority
    ttl: Optional[int] = None  # Time-to-live in seconds (for expirable messages)
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata
    
    def __post_init__(self):
        """Validate and perform any post-initialization setup."""
        # Convert MessageType enum to string for serialization if needed
        if isinstance(self.type, MessageType):
            self.type_name = self.type.name
        else:
            # If passed as string, try to convert to enum
            try:
                self.type = MessageType[self.type]
                self.type_name = self.type.name
            except (KeyError, TypeError):
                raise ValueError(f"Invalid message type: {self.type}")
    
    def is_expired(self) -> bool:
        """
        Check if this message has expired based on its TTL.
        
        Returns:
            bool: True if the message has expired, False otherwise
        """
        if self.ttl is None:
            return False
        current_time = time.time()
        return (current_time - self.timestamp) > self.ttl
    
    def with_content(self, **kwargs) -> 'Message':
        """
        Create a new message with updated content based on this message.
        
        Args:
            **kwargs: Key-value pairs to update in the content dictionary
            
        Returns:
            Message: A new message with updated content
        """
        # Create a shallow copy of the content dictionary
        new_content = dict(self.content)
        
        # Update with the provided key-value pairs
        new_content.update(kwargs)
        
        # Create a new message with the updated content
        return Message(
            type=self.type,
            content=new_content,
            sender=self.sender,
            recipient=self.recipient,
            parent_id=self.message_id,  # Set the new message's parent to this message
            context_id=self.context_id,
            thread_id=self.thread_id,
            priority=self.priority,
            ttl=self.ttl,
            metadata=dict(self.metadata)
        )
    
    def create_reply(self, message_type: MessageType, content: Dict[str, Any]) -> 'Message':
        """
        Create a reply to this message.
        
        Args:
            message_type (MessageType): Type of the reply message
            content (Dict[str, Any]): Content of the reply message
            
        Returns:
            Message: A new message that is a reply to this message
        """
        return Message(
            type=message_type,
            content=content,
            sender=self.recipient,
            recipient=self.sender,
            parent_id=self.message_id,
            context_id=self.context_id,
            thread_id=self.thread_id,
            priority=self.priority,
            metadata=dict(self.metadata)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the message to a dictionary for serialization.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the message
        """
        return {
            "message_id": self.message_id,
            "type": self.type_name,
            "content": self.content,
            "sender": self.sender,
            "recipient": self.recipient,
            "timestamp": self.timestamp,
            "parent_id": self.parent_id,
            "context_id": self.context_id,
            "thread_id": self.thread_id,
            "priority": self.priority,
            "ttl": self.ttl,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """
        Create a message from a dictionary.
        
        Args:
            data (Dict[str, Any]): Dictionary representation of a message
            
        Returns:
            Message: A new message created from the dictionary
        """
        # Handle the message type conversion
        msg_type = data.pop("type")
        if isinstance(msg_type, str):
            try:
                msg_type = MessageType[msg_type]
            except KeyError:
                raise ValueError(f"Invalid message type: {msg_type}")
        
        # Create the message from the dictionary
        return cls(
            type=msg_type,
            content=data.get("content", {}),
            sender=data.get("sender"),
            recipient=data.get("recipient"),
            timestamp=data.get("timestamp", time.time()),
            message_id=data.get("message_id", str(uuid.uuid4())),
            parent_id=data.get("parent_id"),
            context_id=data.get("context_id"),
            thread_id=data.get("thread_id"),
            priority=data.get("priority", 0),
            ttl=data.get("ttl"),
            metadata=data.get("metadata", {})
        )
