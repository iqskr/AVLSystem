from google.transit import gtfs_realtime_pb2

def inspect_message(message_type, indent=0):
    """Inspect a protobuf message type and print its structure."""
    print(" " * indent + f"Message: {message_type.__name__}")
    
    # Get field descriptors
    for field in message_type.DESCRIPTOR.fields:
        print(" " * (indent + 2) + f"Field: {field.name} (#{field.number})")
        
        # Print field type
        print(" " * (indent + 4) + f"Type: {field.type}")
        
        # If it's a message type, try to get the name
        if field.message_type:
            print(" " * (indent + 4) + f"Message type: {field.message_type.full_name}")

# Inspect FeedMessage
print("Inspecting FeedMessage:")
inspect_message(gtfs_realtime_pb2.FeedMessage)

# Create a simple test message
feed = gtfs_realtime_pb2.FeedMessage()
try:
    # Try different potential field names based on standard GTFS-realtime
    try:
        feed.header.gtfs_realtime_version = "2.0"
    except:
        try:
            feed.gtfs_realtime_version = "2.0"
        except:
            print("Could not set gtfs_realtime_version")
    
    # Add an entity
    entity = feed.entity.add()
    entity.id = "test_entity"
    
    # Try to set vehicle position fields
    try:
        entity.vehicle.position.latitude = 12.34
        entity.vehicle.position.longitude = 56.78
    except:
        try:
            entity.vehicle.latitude = 12.34
            entity.vehicle.longitude = 56.78
        except:
            print("Could not set vehicle position")
    
    # Print the serialized message
    serialized = feed.SerializeToString()
    print("\nSerialized message (first 50 bytes):", serialized[:50])
    
except Exception as e:
    print(f"Error creating test message: {e}")

# Print available fields directly
print("\nAvailable fields in FeedMessage:")
feed = gtfs_realtime_pb2.FeedMessage()
for field_name in dir(feed):
    if not field_name.startswith('_') and not callable(getattr(feed, field_name)):
        print(f"  {field_name}: {type(getattr(feed, field_name))}")

print("\nTrying to create a valid message:")
feed = gtfs_realtime_pb2.FeedMessage()
# Set the timestamp field which is common in GTFS-realtime
feed.timestamp = int(1234567890)

entity = feed.entity.add()
entity.id = "test_entity"

# Print what we've created
print(f"Feed timestamp: {feed.timestamp}")
print(f"First entity ID: {entity.id}")
print(f"Entity count: {len(feed.entity)}")

serialized = feed.SerializeToString()
print(f"Serialized length: {len(serialized)} bytes") 