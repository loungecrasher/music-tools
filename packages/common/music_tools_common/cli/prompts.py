"""
User prompts and input handling.
"""
from typing import List, Optional


def prompt_user(message: str, default: Optional[str] = None) -> str:
    """Prompt user for input."""
    if default:
        message = f"{message} [{default}]"

    response = input(f"{message}: ").strip()
    return response or default or ''


def prompt_choice(message: str, choices: List[str]) -> Optional[str]:
    """Prompt user to select from choices."""
    print(f"\n{message}")
    for i, choice in enumerate(choices, 1):
        print(f"{i}. {choice}")

    try:
        idx = int(input("\nEnter choice: ")) - 1
        if 0 <= idx < len(choices):
            return choices[idx]
    except ValueError:
        pass

    return None
