from typing import Any, Dict

def extract_message_content(message: Dict[str, Any]) -> str:
    """
    Extract text content from a message object, handling both string content
    and list-based content structures.
    
    Args:
        message: A dictionary containing message data with a 'content' key
               that is either a string or a list of objects with 'text' attributes
    
    Returns:
        str: The combined text content from the message
    """
    if isinstance(message['content'], list):
        return "\n".join([content.text for content in message['content'] if hasattr(content, 'text')])
    return message['content']

__all__ = ["extract_message_content"]