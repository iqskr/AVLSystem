import os
from google.transit import gtfs_realtime_pb2

def read_proto_file(file_path):
    """Read and decode a protobuf file"""
    feed_message = gtfs_realtime_pb2.FeedMessage()
    
    try:
        with open(file_path, 'rb') as f:
            feed_message.ParseFromString(f.read())
            
        print(f"\nReading file: {file_path}")
        print(f"GTFS Realtime Version: {feed_message.header.gtfs_realtime_version}")
        print(f"Timestamp: {feed_message.header.timestamp}")
        
        for entity in feed_message.entity:
            print(f"\nEntity ID: {entity.id}")
            
            if entity.HasField('vehicle'):
                vehicle = entity.vehicle
                print("Vehicle Position:")
                print(f"  Trip ID: {vehicle.trip.trip_id}")
                print(f"  Route ID: {vehicle.trip.route_id}")
                print(f"  Vehicle ID: {vehicle.vehicle.id}")
                print(f"  Latitude: {vehicle.position.latitude}")
                print(f"  Longitude: {vehicle.position.longitude}")
                print(f"  Speed: {vehicle.position.speed}")
                print(f"  Timestamp: {vehicle.timestamp}")
                print(f"  Current Status: {vehicle.current_status}")
                
            elif entity.HasField('trip_update'):
                trip_update = entity.trip_update
                print("Trip Update:")
                print(f"  Trip ID: {trip_update.trip.trip_id}")
                print(f"  Route ID: {trip_update.trip.route_id}")
                print(f"  Timestamp: {trip_update.timestamp}")
                print(f"  Delay: {trip_update.delay}")
                
                for stop_time_update in trip_update.stop_time_update:
                    print(f"  Stop Time Update:")
                    print(f"    Stop ID: {stop_time_update.stop_id}")
                    print(f"    Stop Sequence: {stop_time_update.stop_sequence}")
                    print(f"    Arrival Time: {stop_time_update.arrival.time}")
                    print(f"    Departure Time: {stop_time_update.departure.time}")
                    
            elif entity.HasField('alert'):
                alert = entity.alert
                print("Service Alert:")
                print(f"  Header: {alert.header_text.translation[0].text}")
                print(f"  Description: {alert.description_text.translation[0].text}")
                print(f"  Cause: {alert.cause}")
                print(f"  Effect: {alert.effect}")
                
                for period in alert.active_period:
                    print(f"  Active Period: {period.start} to {period.end}")
                    
                for entity in alert.informed_entity:
                    print(f"  Affected Route: {entity.route_id}")
                    
    except Exception as e:
        print(f"Error reading file: {e}")

if __name__ == "__main__":
    output_dir = "output"
    message_types = ['vehicle_positions', 'trip_updates', 'service_alerts']
    
    for message_type in message_types:
        type_dir = os.path.join(output_dir, message_type)
        if not os.path.exists(type_dir):
            print(f"\nNo {message_type} directory found.")
            continue
            
        print(f"\nProcessing {message_type}:")
        for filename in os.listdir(type_dir):
            if filename.endswith(".pb"):
                file_path = os.path.join(type_dir, filename)
                read_proto_file(file_path) 