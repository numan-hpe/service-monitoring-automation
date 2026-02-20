"""Shared error processing utilities for Grafana and Humio automation."""
import re
from collections import Counter


def _ordinal(n: int) -> str:
    """Convert integer to ordinal string (e.g., 1 -> '1st', 2 -> '2nd')."""
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _extract_main_error(error_text):
    """Extract only the main error message, removing IDs and identifiers for better grouping."""
    # Remove leading dashes/brackets and spaces
    error_text = re.sub(r'^[\]\-\s]+', '', error_text)
    
    # Remove any existing "occurred X time(s)" patterns
    error_text = re.sub(r'\s*-\s*occurred\s+\d+\s+times?\s*', ' ', error_text, flags=re.IGNORECASE)
    
    # Remove leading IDs and timestamps
    error_text = re.sub(r'^(?:[a-f0-9]{16,}\s+){1,3}', '', error_text)
    error_text = re.sub(r'^[a-f0-9-]{30,}\s+', '', error_text)
    
    # Remove file paths and line numbers
    error_text = re.sub(r'^[\w.]+:\d+\s+', '', error_text)
    
    # Strip device IDs and serial numbers
    error_text = re.sub(r'\b[A-Z0-9]{8,12}\b', '[DEVICE_ID]', error_text)
    
    # Remove UUIDs
    error_text = re.sub(r'\b[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\b', '[UUID]', error_text, flags=re.IGNORECASE)
    
    # Remove pcid values
    error_text = re.sub(r'\bpcid\s+[a-zA-Z0-9]+', 'pcid [ID]', error_text, flags=re.IGNORECASE)
    
    # Remove device references
    error_text = re.sub(r'\bfor device\s+\[DEVICE_ID\]', 'for device', error_text, flags=re.IGNORECASE)
    error_text = re.sub(r'\bfor device:\s*\[DEVICE_ID\]', 'for device', error_text, flags=re.IGNORECASE)
    error_text = re.sub(r'\bdevice:\s*\[DEVICE_ID\]\s*$', 'device', error_text, flags=re.IGNORECASE)
    
    # Remove IP addresses and ports
    error_text = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(:\d+)?\b', '[IP]', error_text)
    
    # Remove AWS/Kafka node addresses
    error_text = re.sub(r'\bb-\d+\.[\w.-]+\.amazonaws\.com(:\d+)?\b', '[KAFKA_NODE]', error_text)
    
    # Remove "Connection at [address]" patterns
    error_text = re.sub(r'Connection at\s+\[(?:IP|KAFKA_NODE)\]', 'Connection', error_text)
    
    # Remove node numbers
    error_text = re.sub(r'\bnode\s+\d+\b', 'node [N]', error_text, flags=re.IGNORECASE)
    
    # Remove "from X:" patterns where X is a number
    error_text = re.sub(r'\bfrom\s+\d+:', 'from [N]:', error_text)
    
    # Clean up leftover spaces
    error_text = re.sub(r'\s+', ' ', error_text).strip()
    error_text = re.sub(r':\s*$', '', error_text)

    # Remove leading module prefixes without line numbers
    module_prefix = re.match(r'^([A-Za-z0-9_.]+):\s+', error_text)
    if module_prefix and '.' in module_prefix.group(1):
        error_text = error_text[module_prefix.end():]
    if re.match(r'^[A-Za-z0-9_.]+$', error_text) and '.' in error_text:
        return ""
    
    # Handle specific error patterns
    if error_text.lower().startswith('template server:'):
        return error_text.split(':', 1)[1].strip()
    if 'Unhandled exception checking is_ready for module' in error_text:
        return 'Unhandled exception checking is_ready for module'
    
    if 'Failed fetch messages' in error_text:
        return 'Failed fetch messages: [Connection Error]'
    
    if 'Heartbeat send request failed' in error_text:
        return 'Heartbeat send request failed: KafkaConnectionError'
    
    if 'Error sending HeartbeatRequest' in error_text or 'Error sending JoinGroupRequest' in error_text:
        if 'HeartbeatRequest' in error_text:
            return 'Error sending HeartbeatRequest'
        else:
            return 'Error sending JoinGroupRequest'
    
    if 'Exception while unregistering device' in error_text:
        return 'Exception while unregistering device'
    if 'Malformed gateway command received' in error_text:
        return 'Malformed gateway command received'
    if 'Invalid message received from gateway' in error_text:
        return 'Invalid message received from gateway'
    if 'ws_producer_handler task exited' in error_text:
        return 'ws_producer_handler task exited for device'
    if 'Compute provision data fetch failed' in error_text:
        error_text = re.sub(r'for device\s+\[DEVICE_ID\]\s+and', 'for device and', error_text)
        return error_text
    if 'Create activation key failed' in error_text:
        return 'Create activation key failed for pcid'
    
    # Extract first sentence or phrase before detailed JSON/dict data
    match = re.match(r'^([^{\[]+?)(?:\s*[{\[]|\s{3,})', error_text)
    if match:
        main_part = match.group(1).strip()
        main_part = re.sub(r':\s*Connection\s*$', '', main_part)
        main_part = re.sub(r'\s+P[0-9A-Z-+]+.*$', '', main_part)
        return main_part.strip()
    
    parts = error_text.split(':')
    if len(parts) >= 2:
        if len(parts) >= 3:
            second_part = parts[1].strip()
            if (second_part.endswith(('Error', 'Exception')) or 
                (second_part and second_part[0].isupper() and 'Error' in second_part)):
                result = f"{parts[0].strip()}: {parts[1].strip()}"
                if len(parts[2].strip()) < 50:
                    result += f": {parts[2].strip()}"
                return result
        if len(parts) == 2:
            first_part = parts[0].strip()
            second_part = parts[1].strip()
            if len(first_part) < 50 and len(second_part) < 100 and len(second_part) > 5:
                return f"{first_part}: {second_part}"
            
        if len(parts[0].strip()) < 20 and len(parts) > 2:
            return f"{parts[0].strip()}: {parts[1].strip()}"
        return parts[0].strip()
    
    if len(error_text) > 150:
        return error_text[:150].strip() + '...'
    return error_text.strip()


def _summarize_errors(errors):
    """Summarize errors by extracting main message and counting occurrences."""
    extracted_errors = [e for e in (_extract_main_error(error) for error in errors) if e]
    counter = Counter(extracted_errors)
    summarized = []
    for text, count in counter.items():
        if count > 1:
            summarized.append(f"{text} - occurred {count} times")
        else:
            summarized.append(text)
    return summarized
