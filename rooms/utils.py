import random
import string

# Exclude visually ambiguous characters
SAFE_CHARS = 'ABCDEFGHJKLMNPQRTUVWXY346789'

def generate_room_code(length=5):
    """Generate a short, unambiguous room code."""
    return ''.join(random.choices(SAFE_CHARS, k=length))