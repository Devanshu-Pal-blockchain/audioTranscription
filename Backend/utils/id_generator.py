"""
ID Generator Utility - Creates random IDs for transcript chunks
"""
import random
import string
import time

def generate_random_id(length: int = 8) -> str:
    """
    Generate a random ID for transcript chunks
    
    Args:
        length: Length of the ID to generate
        
    Returns:
        Random string ID
    """
    # Use uppercase letters and digits for better readability
    characters = string.ascii_uppercase + string.digits
    # Add timestamp component to make it more unique
    timestamp_suffix = str(int(time.time()))[-4:]  # Last 4 digits of timestamp
    random_part = ''.join(random.choice(characters) for _ in range(length - 4))
    return random_part + timestamp_suffix

def generate_session_id() -> str:
    """
    Generate a unique session ID for recording sessions
    
    Returns:
        Session ID string
    """
    return f"SESSION_{generate_random_id(12)}"

def generate_chunk_id(session_id: str, chunk_number: int) -> str:
    """
    Generate a chunk ID based on session ID and chunk number
    
    Args:
        session_id: The session ID
        chunk_number: The chunk number in sequence
        
    Returns:
        Chunk ID string
    """
    return f"{session_id}_CHUNK_{chunk_number:03d}"
