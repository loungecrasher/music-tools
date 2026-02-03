"""
Configuration validation utilities.
"""
import os
import re
from typing import List, Dict, Any
import logging

logger = logging.getLogger('music_tools_common.config.validation')


def validate_spotify_config(config: Dict[str, Any]) -> List[str]:
    """Validate Spotify configuration.

    Args:
        config: Spotify configuration dictionary

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    client_id = config.get('client_id', '')
    client_secret = config.get('client_secret', '')
    redirect_uri = config.get('redirect_uri', '')

    if not client_id:
        errors.append("Missing Spotify client_id")
    elif len(client_id) != 32:
        errors.append(f"Invalid Spotify client_id length: {len(client_id)} (expected 32)")

    if not client_secret:
        errors.append("Missing Spotify client_secret")
    elif len(client_secret) != 32:
        errors.append(f"Invalid Spotify client_secret length: {len(client_secret)} (expected 32)")

    if not redirect_uri:
        errors.append("Missing Spotify redirect_uri")
    elif not redirect_uri.startswith(('http://', 'https://')):
        errors.append("Spotify redirect_uri must start with http:// or https://")

    return errors


def validate_deezer_config(config: Dict[str, Any]) -> List[str]:
    """Validate Deezer configuration.

    Args:
        config: Deezer configuration dictionary

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    email = config.get('email', '')

    if not email:
        errors.append("Missing Deezer email")
    else:
        # Basic email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            errors.append(f"Invalid Deezer email format: {email}")

    return errors


def validate_anthropic_config(config: Dict[str, Any]) -> List[str]:
    """Validate Anthropic configuration.

    Args:
        config: Anthropic configuration dictionary

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    api_key = config.get('api_key', '')
    model = config.get('model', '')

    if not api_key:
        errors.append("Missing Anthropic api_key")
    elif not api_key.startswith('sk-'):
        errors.append("Invalid Anthropic api_key format (should start with 'sk-')")

    if not model:
        errors.append("Missing Anthropic model")

    return errors


def validate_config(service: str, config: Dict[str, Any]) -> List[str]:
    """Validate configuration for a service.

    Args:
        service: Service name
        config: Configuration dictionary

    Returns:
        List of validation errors (empty if valid)
    """
    validators = {
        'spotify': validate_spotify_config,
        'deezer': validate_deezer_config,
        'anthropic': validate_anthropic_config,
    }

    validator = validators.get(service)
    if validator:
        return validator(config)
    else:
        logger.warning(f"No validator found for service: {service}")
        return []


def validate_path(path: str, must_exist: bool = False, create_if_missing: bool = False) -> List[str]:
    """Validate a file or directory path.

    Args:
        path: Path to validate
        must_exist: Whether the path must already exist
        create_if_missing: Whether to create the path if it doesn't exist

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    if not path:
        errors.append("Path is empty")
        return errors

    # Expand user directory
    expanded_path = os.path.expanduser(path)

    if must_exist and not os.path.exists(expanded_path):
        errors.append(f"Path does not exist: {path}")
    elif create_if_missing and not os.path.exists(expanded_path):
        try:
            os.makedirs(expanded_path, exist_ok=True)
            logger.info(f"Created directory: {path}")
        except Exception as e:
            errors.append(f"Could not create path {path}: {e}")

    return errors
