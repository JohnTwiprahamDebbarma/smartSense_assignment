"""
Base agent class that defines the common interface and functionality for all agents.
"""

import os
import logging
import yaml
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

from ..core.message import Message
from ..core.config import load_config

class BaseAgent(ABC):
    """
    Abstract base class for all agents in the system.
    
    All specialized agents should inherit from this class and implement
    the required abstract methods.
    """
    
    def __init__(self, agent_type: str, config_path: Optional[str] = None):
        """
        Initialize the base agent with configuration and setup logging.
        
        Args:
            agent_type (str): Type of agent (transcriber, semantic_parser, etc.)
            config_path (Optional[str]): Path to custom config file
        """
        self.agent_type = agent_type
        self.logger = logging.getLogger(f"agent.{agent_type}")
        
        # I'm loading configuration from YAML files
        self.config = load_config(config_path)
        self.agent_config = self.config["agents"].get(agent_type, {})
        
        # Load agent-specific prompts if they exist
        self.prompts = {}
        prompt_path = os.path.join("config", "prompts", f"{agent_type}_prompts.yaml")
        if os.path.exists(prompt_path):
            with open(prompt_path, "r") as f:
                self.prompts = yaml.safe_load(f)
            self.logger.info(f"Loaded prompts for {agent_type} agent")
        
        # These will be set when the agent is registered with the event bus
        self.event_bus = None
        self.agent_id = None
        
        self.logger.info(f"Initialized {agent_type} agent")
    
    def register(self, event_bus, agent_id: str):
        """
        Register the agent with the event bus to enable message passing.
        
        Args:
            event_bus: The event bus instance for agent communication
            agent_id (str): Unique identifier for this agent instance
        """
        self.event_bus = event_bus
        self.agent_id = agent_id
        self.logger.info(f"Agent {agent_id} registered with event bus")
        
        # Subscribe to relevant event types
        event_types = self.get_subscribed_events()
        for event_type in event_types:
            self.event_bus.subscribe(event_type, self.process_message)
            
        self.logger.info(f"Subscribed to events: {event_types}")
    
    def send_message(self, message: Message):
        """
        Send a message through the event bus.
        
        Args:
            message (Message): The message to send
        """
        if self.event_bus is None:
            self.logger.error("Cannot send message: Agent not registered with event bus")
            return
            
        message.sender = self.agent_id
        self.event_bus.publish(message)
        self.logger.debug(f"Sent message of type {message.type}")
    
    def process_message(self, message: Message):
        """
        Process an incoming message from the event bus.
        
        Args:
            message (Message): The message to process
        """
        if message.sender == self.agent_id:
            # Don't process our own messages
            return
            
        self.logger.debug(f"Processing message of type {message.type} from {message.sender}")
        
        # Delegate to the handle_message method for agent-specific processing
        self.handle_message(message)
    
    @abstractmethod
    def handle_message(self, message: Message):
        """
        Handle a specific message for this agent type.
        Must be implemented by each specific agent.
        
        Args:
            message (Message): The message to handle
        """
        pass
    
    @abstractmethod
    def get_subscribed_events(self) -> List[str]:
        """
        Return a list of event types this agent subscribes to.
        Must be implemented by each specific agent.
        
        Returns:
            List[str]: List of event types
        """
        pass
    
    def get_prompt(self, prompt_key: str, **kwargs) -> str:
        """
        Get a prompt template and format it with the provided arguments.
        
        Args:
            prompt_key (str): The key for the prompt in the prompts dictionary
            **kwargs: Arguments to format the prompt with
            
        Returns:
            str: The formatted prompt
        """
        if prompt_key not in self.prompts:
            self.logger.warning(f"Prompt key '{prompt_key}' not found in prompts for {self.agent_type}")
            return ""
            
        prompt_template = self.prompts[prompt_key]
        try:
            formatted_prompt = prompt_template.format(**kwargs)
            return formatted_prompt
        except KeyError as e:
            self.logger.error(f"Error formatting prompt '{prompt_key}': {e}")
            return prompt_template
    
    def log_error(self, error_msg: str, exception: Optional[Exception] = None):
        """
        Log an error and include exception details if provided.
        
        Args:
            error_msg (str): The error message
            exception (Optional[Exception]): The exception that caused the error
        """
        if exception:
            self.logger.error(f"{error_msg}: {str(exception)}", exc_info=True)
        else:
            self.logger.error(error_msg)
