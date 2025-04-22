"""
Event bus for asynchronous communication between agents.
Implements a publisher-subscriber pattern.
"""

import logging
from typing import Dict, List, Callable, Any
from collections import defaultdict
import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor

from .message import Message

class EventBus:
    """
    Event bus for agent communication using a publisher-subscriber pattern.
    
    Agents can subscribe to specific event types and publish events to the bus.
    The bus will deliver events to all subscribers of that event type.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the event bus.
        
        Args:
            config (Dict[str, Any], optional): Configuration for the event bus
        """
        self.logger = logging.getLogger("core.event_bus")
        self.config = config or {}
        
        # Dictionary of event_type -> list of subscribers
        self.subscribers = defaultdict(list)
        
        # Thread pool for concurrent event handling
        self.executor = ThreadPoolExecutor(
            max_workers=self.config.get("max_workers", 10)
        )
        
        # Event loop for async operation
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Dictionary to store message history for debugging
        self.message_history = []
        self.max_history_size = self.config.get("max_history_size", 1000)
        
        self.logger.info("Event bus initialized")
    
    def subscribe(self, event_type: str, callback: Callable[[Message], None]) -> str:
        """
        Subscribe to a specific event type.
        
        Args:
            event_type (str): The type of event to subscribe to
            callback (Callable): Function to call when an event of this type is published
            
        Returns:
            str: Subscription ID that can be used to unsubscribe
        """
        subscription_id = str(uuid.uuid4())
        self.subscribers[event_type].append((subscription_id, callback))
        self.logger.debug(f"Added subscription to {event_type}, ID: {subscription_id}")
        return subscription_id
    
    def unsubscribe(self, event_type: str, subscription_id: str) -> bool:
        """
        Unsubscribe from a specific event type using the subscription ID.
        
        Args:
            event_type (str): The event type to unsubscribe from
            subscription_id (str): The subscription ID to remove
            
        Returns:
            bool: True if unsubscribed successfully, False otherwise
        """
        if event_type not in self.subscribers:
            return False
            
        initial_length = len(self.subscribers[event_type])
        self.subscribers[event_type] = [
            (sub_id, callback) 
            for sub_id, callback in self.subscribers[event_type] 
            if sub_id != subscription_id
        ]
        
        success = len(self.subscribers[event_type]) < initial_length
        if success:
            self.logger.debug(f"Removed subscription to {event_type}, ID: {subscription_id}")
        
        # Clean up empty event types
        if not self.subscribers[event_type]:
            del self.subscribers[event_type]
            
        return success
    
    def publish(self, message: Message) -> None:
        """
        Publish a message to all subscribers of its event type.
        
        Args:
            message (Message): The message to publish
        """
        if not isinstance(message, Message):
            self.logger.error(f"Cannot publish: expected Message object, got {type(message)}")
            return
        
        # Add to message history
        if len(self.message_history) >= self.max_history_size:
            self.message_history.pop(0)  # Remove oldest message
        self.message_history.append(message)
        
        # Get all subscribers for this event type
        event_type = message.type
        if event_type not in self.subscribers:
            self.logger.debug(f"No subscribers for event type: {event_type}")
            return
            
        subscriber_count = len(self.subscribers[event_type])
        self.logger.debug(f"Publishing {event_type} event to {subscriber_count} subscribers")
        
        # Process in event loop to ensure thread safety
        for _, callback in self.subscribers[event_type]:
            asyncio.run_coroutine_threadsafe(
                self._async_call_subscriber(callback, message),
                self.loop
            )
    
    async def _async_call_subscriber(self, callback: Callable, message: Message) -> None:
        """
        Asynchronously call a subscriber callback with a message.
        
        Args:
            callback (Callable): The subscriber callback
            message (Message): The message to pass to the callback
        """
        try:
            # Run callback in thread pool to avoid blocking
            await self.loop.run_in_executor(
                self.executor,
                lambda: callback(message)
            )
        except Exception as e:
            self.logger.error(f"Error in subscriber callback: {str(e)}", exc_info=True)
    
    def get_recent_messages(self, limit: int = 50) -> List[Message]:
        """
        Get the most recent messages for debugging purposes.
        
        Args:
            limit (int): Maximum number of messages to return
            
        Returns:
            List[Message]: List of recent messages
        """
        return self.message_history[-limit:] if self.message_history else []
    
    def shutdown(self) -> None:
        """Shut down the event bus and release resources."""
        self.logger.info("Shutting down event bus")
        self.executor.shutdown(wait=True)
        
        # Cancel all pending tasks
        for task in asyncio.all_tasks(self.loop):
            task.cancel()
            
        # Close the event loop
        self.loop.close()
        self.logger.info("Event bus shut down")
