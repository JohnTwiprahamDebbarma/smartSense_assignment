"""
Configuration management for the board meeting agent system.
Handles loading and parsing configuration files and environment variables.
"""

import os
import logging
import yaml
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Set up logger for this module
logger = logging.getLogger("core.config")

# Load environment variables from .env file
load_dotenv()

def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from YAML files and environment variables.
    
    Args:
        config_path (Optional[str]): Path to a custom config file
        
    Returns:
        Dict[str, Any]: Merged configuration dictionary
    """
    # Default config path
    default_config_path = os.path.join("config", "system_config.yaml")
    
    # Start with empty config
    config = {}
    
    # Load from default config file if it exists
    if os.path.exists(default_config_path):
        with open(default_config_path, "r") as f:
            try:
                default_config = yaml.safe_load(f)
                if default_config:
                    config.update(default_config)
                logger.info(f"Loaded configuration from {default_config_path}")
            except yaml.YAMLError as e:
                logger.error(f"Error parsing default config file: {e}")
    
    # Load from custom config file if provided and it exists
    if config_path and os.path.exists(config_path):
        with open(config_path, "r") as f:
            try:
                custom_config = yaml.safe_load(f)
                if custom_config:
                    # Deep merge the custom config into the default config
                    deep_merge(config, custom_config)
                logger.info(f"Loaded custom configuration from {config_path}")
            except yaml.YAMLError as e:
                logger.error(f"Error parsing custom config file: {e}")
    
    # Load agent-specific configs from separate files
    agent_config_dir = os.path.join("config", "agent_config.yaml")
    if os.path.exists(agent_config_dir):
        with open(agent_config_dir, "r") as f:
            try:
                agent_config = yaml.safe_load(f)
                if agent_config and "agents" in agent_config:
                    # If 'agents' key doesn't exist in config, create it
                    if "agents" not in config:
                        config["agents"] = {}
                    # Merge each agent's config
                    for agent_name, agent_settings in agent_config["agents"].items():
                        if agent_name not in config["agents"]:
                            config["agents"][agent_name] = {}
                        config["agents"][agent_name].update(agent_settings)
                logger.info(f"Loaded agent configurations from {agent_config_dir}")
            except yaml.YAMLError as e:
                logger.error(f"Error parsing agent config file: {e}")
    
    # Process environment variable references in the config
    config = process_env_vars(config)
    
    return config

def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> None:
    """
    Recursively merge two dictionaries, modifying the base dictionary in-place.
    
    Args:
        base (Dict[str, Any]): Base dictionary to merge into
        override (Dict[str, Any]): Dictionary with values to override
    """
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            # If both values are dictionaries, merge them recursively
            deep_merge(base[key], value)
        else:
            # Otherwise, override the value in the base dictionary
            base[key] = value

def process_env_vars(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process environment variable references in the configuration.
    
    Args:
        config (Dict[str, Any]): Configuration dictionary
        
    Returns:
        Dict[str, Any]: Configuration with environment variables replaced
    """
    if isinstance(config, dict):
        for key, value in config.items():
            if isinstance(value, (dict, list)):
                # Recursively process nested dictionaries and lists
                config[key] = process_env_vars(value)
            elif isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                # Extract environment variable name
                env_var = value[2:-1]
                env_value = os.environ.get(env_var)
                
                if env_value is not None:
                    # Replace the reference with the actual value
                    config[key] = env_value
                    logger.debug(f"Replaced environment variable {env_var} in config")
                else:
                    # Keep the reference if the environment variable doesn't exist
                    logger.warning(f"Environment variable {env_var} not found")
    elif isinstance(config, list):
        # Process each item in the list
        for i, item in enumerate(config):
            config[i] = process_env_vars(item)
    
    return config

def get_required_env_vars() -> Dict[str, str]:
    """
    List all required environment variables and their values.
    Only used for setup verification.
    
    Returns:
        Dict[str, str]: Dictionary of required environment variables and their values
    """
    required_vars = [
        "OPENAI_API_KEY",
        "JIRA_BASE_URL",
        "JIRA_USERNAME",
        "JIRA_API_TOKEN",
        "SLACK_BOT_TOKEN",
        "SMTP_SERVER",
        "EMAIL_USERNAME",
        "EMAIL_PASSWORD"
    ]
    
    env_vars = {}
    missing_vars = []
    
    for var in required_vars:
        value = os.environ.get(var)
        if value:
            # Mask sensitive values for logging
            if "API_KEY" in var or "TOKEN" in var or "PASSWORD" in var:
                masked_value = value[:4] + "*" * (len(value) - 4)
                env_vars[var] = masked_value
            else:
                env_vars[var] = value
        else:
            missing_vars.append(var)
    
    if missing_vars:
        logger.warning(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    return env_vars

def save_config(config: Dict[str, Any], file_path: str) -> bool:
    """
    Save a configuration dictionary to a YAML file.
    
    Args:
        config (Dict[str, Any]): Configuration to save
        file_path (str): Path where to save the configuration
        
    Returns:
        bool: True if saved successfully, False otherwise
    """
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False)
        
        logger.info(f"Configuration saved to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving configuration to {file_path}: {e}")
        return False
