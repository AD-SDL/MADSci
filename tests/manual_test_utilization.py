"""
Debug script to understand the difference between client API and direct MongoDB access.
"""

from madsci.client.event_client import EventClient
from madsci.common.types.event_types import EventType
import json

def compare_data_pathways():
    """Compare how events look via API vs direct MongoDB access."""
    
    print("=== COMPARING DATA PATHWAYS ===")
    
    # Method 1: Via Client API (what your simple script uses)
    print("\\n1. Via Client API (/events endpoint):")
    client = EventClient()
    events_via_api = client.get_events(number=100)
    
    workcell_via_api = None
    for event_id, event in events_via_api.items():
        if event.event_type == EventType.WORKCELL_START:
            workcell_via_api = (event_id, event)
            break
    
    if workcell_via_api:
        event_id, event = workcell_via_api
        print(f"  Found WORKCELL_START via API: {event_id}")
        print(f"  event.event_type: {event.event_type} (type: {type(event.event_type)})")
        print(f"  event.event_type.value: {event.event_type.value}")
        print(f"  isinstance(event.event_type, EventType): {isinstance(event.event_type, EventType)}")
        
        # Show the raw model dump (how it gets serialized)
        raw_data = event.model_dump()
        print(f"  Raw model dump event_type: {raw_data['event_type']} (type: {type(raw_data['event_type'])})")
        
        # Show JSON serialization
        json_data = event.model_dump(mode="json")
        print(f"  JSON mode event_type: {json_data['event_type']} (type: {type(json_data['event_type'])})")
    else:
        print("  ❌ No WORKCELL_START found via API")
    
    # Method 2: Simulate what the server analyzer sees (direct MongoDB access)
    print("\\n2. How the server analyzer sees the data:")
    
    # The server does this kind of query:
    print("  Server query looks for: {'event_type': {'$in': ['workcell_start', ...]}}")
    
    # Let's simulate what MongoDB would return by checking how events are stored
    if workcell_via_api:
        event_id, event = workcell_via_api
        
        # This is what gets stored in MongoDB (via the Event.to_mongo() method)
        try:
            mongo_data = event.to_mongo()
            print(f"  MongoDB stored event_type: {mongo_data.get('event_type')} (type: {type(mongo_data.get('event_type'))})")
        except Exception as e:
            print(f"  Error calling to_mongo(): {e}")
            # Fallback - show what model_dump gives us
            mongo_data = event.model_dump(mode="json")
            print(f"  Model dump event_type: {mongo_data.get('event_type')} (type: {type(mongo_data.get('event_type'))})")
        
        # Test if the query would match
        stored_event_type = mongo_data.get('event_type')
        query_types = ['workcell_start', 'lab_start']
        would_match = stored_event_type in query_types
        print(f"  Would query match? {stored_event_type} in {query_types} = {would_match}")

def test_event_serialization():
    """Test how EventType enums are serialized."""
    
    print("\\n=== TESTING EVENT SERIALIZATION ===")
    
    # Test direct enum serialization
    enum_val = EventType.WORKCELL_START
    print(f"Direct enum: {enum_val}")
    print(f"Enum value: {enum_val.value}")
    print(f"String of enum: {str(enum_val)}")
    
    # Test JSON serialization
    try:
        import json
        json_str = json.dumps(enum_val, default=str)
        print(f"JSON serialized: {json_str}")
    except Exception as e:
        print(f"JSON serialization error: {e}")
    
    # Test how Pydantic handles it
    from madsci.common.types.event_types import Event
    from datetime import datetime
    
    test_event = Event(
        event_type=EventType.WORKCELL_START,
        event_data={"test": "data"}
    )
    
    print(f"\\nTest Event:")
    print(f"  event_type: {test_event.event_type}")
    print(f"  model_dump(): {test_event.model_dump()['event_type']}")
    print(f"  model_dump(mode='json'): {test_event.model_dump(mode='json')['event_type']}")

def check_server_event_collection():
    """Check what the server's event collection actually contains."""
    
    print("\\n=== CHECKING SERVER EVENT COLLECTION ===")
    
    # We can't directly access the server's MongoDB from here,
    # but we can make educated guesses based on the API response
    
    client = EventClient()
    
    # The /events endpoint processes events through this code in your server:
    # ```python
    # event_list = events.find({"log_level": {"$gte": level}}).sort("event_timestamp", -1).limit(number).to_list()
    # return {event["_id"]: event for event in event_list}
    # ```
    
    # This suggests that events.find() returns raw MongoDB documents
    # Let's see what those look like by examining the API response structure
    
    events = client.get_events(number=5)
    print(f"API returned {len(events)} events")
    
    for event_id, event in events.items():
        print(f"\\nEvent {event_id}:")
        print(f"  Type: {type(event)}")
        print(f"  event_type: {event.event_type} (type: {type(event.event_type)})")
        
        # The key insight: The API converts raw MongoDB docs back to Event objects
        # But the analyzer works with raw MongoDB docs directly
        break

if __name__ == "__main__":
    compare_data_pathways()
    test_event_serialization() 
    check_server_event_collection()