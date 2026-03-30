"""
Response sanitizer to clean up corrupted model output
"""
import html
import re
from typing import Optional


def sanitize_response(response: str) -> str:
    """
    Clean up corrupted model output.
    
    Handles:
    - HTML entity decoding (&gt; → >, &quot; → ", etc)
    - Removing control characters
    - Collapsing excessive whitespace
    - Removing garbled Unicode patterns
    """
    if not response:
        return response
    
    # Step 1: Decode HTML entities
    try:
        response = html.unescape(response)
    except Exception:
        pass
    
    # Step 2: Remove common corruption patterns
    # Remove excessive backslashes
    response = re.sub(r'\\{2,}', '\\', response)
    
    # Remove excessive quotes
    response = re.sub(r'"{2,}', '"', response)
    
    # Step 3: Remove control characters but keep newlines/tabs
    response = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', response)
    
    # Step 4: Fix broken UTF-8 sequences
    # Replace mojibake patterns with space
    response = re.sub(r'[^\x00-\x7f](?![^\x80-\xbf])', ' ', response)
    
    # Step 5: Collapse excessive whitespace
    response = re.sub(r' {2,}', ' ', response)
    response = re.sub(r'\n{3,}', '\n\n', response)
    
    # Step 6: Clean up artifact patterns (e.g., repeated ":")
    response = re.sub(r':"{2,}', ':', response)
    
    # Step 7: Ensure proper sentence termination
    response = response.strip()
    if response and not response.endswith(('.', '!', '?', ':', ';')):
        response += '.'
    
    return response


if __name__ == "__main__":
    # Test
    corrupted = 'Cr&gt: 1this #&quot & \\1 \\\"1 \\\\f.*)   <!--": "*** ": " ": ... [garbled]'
    clean = sanitize_response(corrupted)
    print(f"Original: {corrupted}")
    print(f"Cleaned:  {clean}")
