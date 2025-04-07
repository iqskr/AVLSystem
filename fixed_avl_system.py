import os
import time
import json
import logging
from datetime import datetime
import pandas as pd
from geopy.distance import geodesic
from google.transit import gtfs_realtime_pb2
from google.protobuf import timestamp_pb2
from dotenv import load_dotenv
import schedule
import requests
import tempfile
import zipfile
import uuid
import math


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AVLSystem:
    def __init__(self):
        load_dotenv()
        self.gps_logger_url = os.getenv('GPS_LOGGER_URL')
        self.gtfs_static_url = os.getenv('GTFS_STATIC_URL')
        self.output_dir = os.getenv('OUTPUT_DIR', 'output')
        self.vehicle_positions = {}
        self.trip_updates = {}
        self.service_alerts = {}
        self.previous_positions = {}  # Store previous positions for bearing calculation
        
        # Load configuration
        self.config = self.load_config()
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)

    def load_config(self):
        """Load configuration from config.json"""
        try:
            with open('config.json', 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {
                "vehicles": {},
                "routes": {}
            }

    def get_vehicle_info(self, vehicle_number):
        """Get vehicle information from config"""
        return self.config.get('vehicles', {}).get(str(vehicle_number), {
            'device_id': str(vehicle_number),
            'label': str(vehicle_number)
        })

    def get_trip_info(self, route_id):
        """Get trip information from config"""
        return self.config.get('routes', {}).get(str(route_id), {}).get('trips', [{}])[0]

    def fetch_gps_data(self):
        """Fetch GPS data from GPSLogger application"""
        try:
            response = requests.get(self.gps_logger_url)
            response.raise_for_status()
            
            # Try to parse as JSON
            try:
                data = response.json()
                logger.info(f"Successfully fetched GPS data as JSON")
                logger.info(f"GPS data structure: {data}")
                return data
            except json.JSONDecodeError:
                # If not JSON, try to handle as plain text
                logger.warning("GPS data is not in JSON format, trying to parse as text")
                text_data = response.text
                logger.info(f"Raw GPS data: {text_data[:200]}...")  # Log first 200 chars
                
                # Create a simple structure with the raw data
                return {"raw_data": text_data}
                
        except Exception as e:
            logger.error(f"Error fetching GPS data: {e}")
            # Return a minimal structure that won't cause further errors
            return {"error": str(e)}

    def fetch_gtfs_static(self):
        """Fetch and process GTFS static data"""
        try:
            response = requests.get(self.gtfs_static_url)
            response.raise_for_status()
            
            # Create a temporary directory for GTFS files
            with tempfile.TemporaryDirectory() as temp_dir:
                # Save the ZIP file
                zip_path = os.path.join(temp_dir, 'gtfs.zip')
                with open(zip_path, 'wb') as f:
                    f.write(response.content)
                
                # Extract the ZIP file
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                # Read and process GTFS files
                gtfs_data = {}
                
                # Read and process routes.txt
                routes_path = os.path.join(temp_dir, 'routes.txt')
                if os.path.exists(routes_path):
                    routes_df = pd.read_csv(routes_path)
                    gtfs_data['routes'] = routes_df.to_dict('records')
                
                # Read and process trips.txt
                trips_path = os.path.join(temp_dir, 'trips.txt')
                if os.path.exists(trips_path):
                    trips_df = pd.read_csv(trips_path)
                    gtfs_data['trips'] = trips_df.to_dict('records')
                
                # Read and process stops.txt
                stops_path = os.path.join(temp_dir, 'stops.txt')
                if os.path.exists(stops_path):
                    stops_df = pd.read_csv(stops_path)
                    gtfs_data['stops'] = stops_df.to_dict('records')
                
                # Read and process stop_times.txt
                stop_times_path = os.path.join(temp_dir, 'stop_times.txt')
                if os.path.exists(stop_times_path):
                    stop_times_df = pd.read_csv(stop_times_path)
                    gtfs_data['stop_times'] = stop_times_df.to_dict('records')
                
                # Read and process calendar.txt or calendar_dates.txt
                calendar_path = os.path.join(temp_dir, 'calendar.txt')
                calendar_dates_path = os.path.join(temp_dir, 'calendar_dates.txt')
                if os.path.exists(calendar_path):
                    calendar_df = pd.read_csv(calendar_path)
                    gtfs_data['calendar'] = calendar_df.to_dict('records')
                elif os.path.exists(calendar_dates_path):
                    calendar_dates_df = pd.read_csv(calendar_dates_path)
                    gtfs_data['calendar_dates'] = calendar_dates_df.to_dict('records')
                
                # Process the data to create a more useful structure
                processed_data = self.process_gtfs_data(gtfs_data)
                return processed_data
                
        except Exception as e:
            logger.error(f"Error fetching GTFS static data: {e}")
            return None

    def process_gtfs_data(self, gtfs_data):
        """Process raw GTFS data into a more useful structure"""
        processed = {
            'routes': {},
            'trips': {},
            'stops': {},
            'stop_sequences': {}
        }
        
        # Process routes
        if 'routes' in gtfs_data:
            for route in gtfs_data['routes']:
                route_id = str(route.get('route_id', ''))
                processed['routes'][route_id] = {
                    'route_id': route_id,
                    'route_name': route.get('route_long_name', ''),
                    'route_type': route.get('route_type', ''),
                    'route_color': route.get('route_color', ''),
                    'route_text_color': route.get('route_text_color', '')
                }
        
        # Process trips
        if 'trips' in gtfs_data:
            for trip in gtfs_data['trips']:
                trip_id = str(trip.get('trip_id', ''))
                route_id = str(trip.get('route_id', ''))
                processed['trips'][trip_id] = {
                    'trip_id': trip_id,
                    'route_id': route_id,
                    'service_id': trip.get('service_id', ''),
                    'direction_id': int(trip.get('direction_id', 0)),
                    'shape_id': trip.get('shape_id', ''),
                    'wheelchair_accessible': trip.get('wheelchair_accessible', '')
                }
        
        # Process stops
        if 'stops' in gtfs_data:
            for stop in gtfs_data['stops']:
                stop_id = str(stop.get('stop_id', ''))
                processed['stops'][stop_id] = {
                    'stop_id': stop_id,
                    'stop_name': stop.get('stop_name', ''),
                    'stop_lat': float(stop.get('stop_lat', 0.0)),
                    'stop_lon': float(stop.get('stop_lon', 0.0)),
                    'stop_code': stop.get('stop_code', ''),
                    'stop_desc': stop.get('stop_desc', '')
                }
        
        # Process stop times and create stop sequences
        if 'stop_times' in gtfs_data:
            for stop_time in gtfs_data['stop_times']:
                trip_id = str(stop_time.get('trip_id', ''))
                stop_id = str(stop_time.get('stop_id', ''))
                stop_sequence = int(stop_time.get('stop_sequence', 0))
                
                if trip_id not in processed['stop_sequences']:
                    processed['stop_sequences'][trip_id] = []
                
                processed['stop_sequences'][trip_id].append({
                    'stop_sequence': stop_sequence,
                    'stop_id': stop_id,
                    'arrival_time': stop_time.get('arrival_time', ''),
                    'departure_time': stop_time.get('departure_time', ''),
                    'stop_headsign': stop_time.get('stop_headsign', ''),
                    'pickup_type': stop_time.get('pickup_type', ''),
                    'drop_off_type': stop_time.get('drop_off_type', '')
                })
        
        # Sort stop sequences by sequence number
        for trip_id in processed['stop_sequences']:
            processed['stop_sequences'][trip_id].sort(key=lambda x: x['stop_sequence'])
        
        return processed

    def get_trip_stops(self, trip_id, gtfs_data):
        """Get all stops for a specific trip"""
        if trip_id in gtfs_data['stop_sequences']:
            stops = []
            for stop_seq in gtfs_data['stop_sequences'][trip_id]:
                stop_id = stop_seq['stop_id']
                if stop_id in gtfs_data['stops']:
                    stop_info = gtfs_data['stops'][stop_id]
                    stops.append({
                        'stop_sequence': stop_seq['stop_sequence'],
                        'stop_id': stop_id,
                        'stop_name': stop_info['stop_name'],
                        'arrival_time': stop_seq['arrival_time'],
                        'departure_time': stop_seq['departure_time']
                    })
            return stops
        return []

    def calculate_bearing(self, lat1, lon1, lat2, lon2):
        """
        Calculate the bearing between two points using the Haversine formula.
        Returns bearing in degrees (0-360, where 0 is North, 90 is East, etc.)
        """
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        dlon = lon2 - lon1
        
        y = math.sin(dlon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        bearing = math.atan2(y, x)
        bearing = math.degrees(bearing)
        bearing = (bearing + 360) % 360  # Normalize to 0-360
        
        return bearing

    def create_vehicle_position(self, gps_data):
        """Create a VehiclePosition protobuf message"""
        feed_message = gtfs_realtime_pb2.FeedMessage()
        
        # Set header fields
        feed_message.header.gtfs_realtime_version = "2.0"
        feed_message.header.timestamp = int(time.time())

        # Create FeedEntity
        entity = feed_message.entity.add()
        entity.id = str(gps_data.get('device_id'))

        # Create VehiclePosition
        vehicle = entity.vehicle
        
        # Set trip information
        vehicle.trip.trip_id = str(gps_data.get('trip_id'))
        vehicle.trip.route_id = str(gps_data.get('route_id'))
        vehicle.trip.direction_id = int(gps_data.get('direction_id', 0))
        
        # Set start date
        current_time = datetime.now()
        vehicle.trip.start_date = current_time.strftime("%Y%m%d")
        
        # Set position information
        try:
            current_lat = float(gps_data.get('latitude', 0.0))
            current_lon = float(gps_data.get('longitude', 0.0))
            device_id = str(gps_data.get('device_id'))
            
            logger.info(f"Processing position for vehicle {device_id}: lat={current_lat}, lon={current_lon}")
            
            vehicle.position.latitude = current_lat
            vehicle.position.longitude = current_lon
            
            # Calculate bearing based on previous position if available
            if device_id in self.previous_positions:
                prev_pos = self.previous_positions[device_id]
                logger.info(f"Previous position found for {device_id}: lat={prev_pos['latitude']}, lon={prev_pos['longitude']}")
                
                # Only calculate bearing if we have valid coordinates
                if (current_lat != 0.0 and current_lon != 0.0 and 
                    prev_pos['latitude'] != 0.0 and prev_pos['longitude'] != 0.0):
                    bearing = self.calculate_bearing(
                        prev_pos['latitude'], prev_pos['longitude'],
                        current_lat, current_lon
                    )
                    logger.info(f"Calculated bearing: {bearing} degrees")
                    vehicle.position.bearing = bearing
                else:
                    logger.warning(f"Invalid coordinates for bearing calculation: current=({current_lat}, {current_lon}), previous=({prev_pos['latitude']}, {prev_pos['longitude']})")
                    vehicle.position.bearing = float(gps_data.get('bearing', 0.0))
            else:
                logger.info(f"No previous position found for {device_id}, using GPS bearing")
                # Try to get bearing from GPS data
                gps_bearing = gps_data.get('bearing')
                if gps_bearing is not None:
                    try:
                        vehicle.position.bearing = float(gps_bearing)
                        logger.info(f"Using GPS bearing: {gps_bearing}")
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid GPS bearing value: {gps_bearing}")
                        vehicle.position.bearing = 0.0
                else:
                    logger.warning("No bearing information available in GPS data")
                    vehicle.position.bearing = 0.0
            
            # Update previous position
            self.previous_positions[device_id] = {
                'latitude': current_lat,
                'longitude': current_lon,
                'timestamp': time.time()
            }
            
        except (ValueError, TypeError) as e:
            logger.error(f"Error converting GPS coordinates: {e}")
            vehicle.position.latitude = 0.0
            vehicle.position.longitude = 0.0
            vehicle.position.bearing = 0.0
        
        # Set vehicle information
        vehicle.vehicle.id = str(gps_data.get('device_id'))
        vehicle.vehicle.label = str(gps_data.get('label', gps_data.get('device_id')))
        
        # Set timestamp
        vehicle.timestamp = int(time.time())

        return feed_message

    def create_trip_update(self, gps_data, gtfs_data):
        """Create a TripUpdate protobuf message"""
        feed_message = gtfs_realtime_pb2.FeedMessage()
        
        # Set header fields
        feed_message.header.gtfs_realtime_version = "2.0"
        feed_message.header.timestamp = int(time.time())

        # Get trip ID from GPS data
        trip_id = str(gps_data.get('trip_id'))
        
        # Create FeedEntity
        entity = feed_message.entity.add()
        entity.id = f"trip_{trip_id}"

        # Create TripUpdate
        trip_update = entity.trip_update
        trip_update.trip.trip_id = trip_id
        trip_update.trip.route_id = str(gps_data.get('route_id'))
        trip_update.trip.direction_id = int(gps_data.get('direction_id', 0))
        
        # Set start time and date
        current_time = datetime.now()
        trip_update.trip.start_time = current_time.strftime("%H:%M:%S")
        trip_update.trip.start_date = current_time.strftime("%Y%m%d")
        
        # Set vehicle information
        trip_update.vehicle.id = str(gps_data.get('device_id'))
        trip_update.vehicle.label = str(gps_data.get('label', gps_data.get('device_id')))
        
        # Set timestamp
        trip_update.timestamp = int(time.time())
        
        # Get stops for this trip from GTFS data
        stops = self.get_trip_stops(trip_id, gtfs_data)
        
        # Add stop time updates
        for stop in stops:
            stop_time_update = trip_update.stop_time_update.add()
            stop_time_update.stop_sequence = int(stop['stop_sequence'])
            stop_time_update.stop_id = str(stop['stop_id'])
            
            # Convert arrival time to Unix timestamp
            if stop['arrival_time']:
                try:
                    arrival_time = datetime.strptime(f"{current_time.strftime('%Y%m%d')} {stop['arrival_time']}", "%Y%m%d %H:%M:%S")
                    stop_time_update.arrival.time = int(arrival_time.timestamp())
                except ValueError as e:
                    logger.error(f"Error converting arrival time: {e}")
                    stop_time_update.arrival.time = int(time.time())
            
            # Convert departure time to Unix timestamp
            if stop['departure_time']:
                try:
                    departure_time = datetime.strptime(f"{current_time.strftime('%Y%m%d')} {stop['departure_time']}", "%Y%m%d %H:%M:%S")
                    stop_time_update.departure.time = int(departure_time.timestamp())
                except ValueError as e:
                    logger.error(f"Error converting departure time: {e}")
                    stop_time_update.departure.time = int(time.time())
            
            # Set schedule relationship (0 = SCHEDULED)
            stop_time_update.schedule_relationship = 0

        return feed_message

    def create_service_alert(self, alert_data):
        """Create a ServiceAlert protobuf message"""
        feed_message = gtfs_realtime_pb2.FeedMessage()
        
        # Set header fields
        feed_message.header.gtfs_realtime_version = "2.0"
        feed_message.header.timestamp = int(time.time())

        # Generate alert ID
        alert_id = alert_data.get('id', str(uuid.uuid4()))
        
        # Create FeedEntity
        entity = feed_message.entity.add()
        entity.id = f"alert_{alert_id}"

        # Create Alert
        alert = entity.alert
        
        # Add header text
        if 'header' in alert_data:
            header = alert.header_text.translation.add()
            header.text = alert_data['header']
        else:
            header = alert.header_text.translation.add()
            header.text = "Service Alert"
        
        # Add description text
        if 'description' in alert_data:
            desc = alert.description_text.translation.add()
            desc.text = alert_data['description']
        else:
            desc = alert.description_text.translation.add()
            desc.text = "No details available"
        
        # Add active period
        time_range = alert.active_period.add()
        time_range.start = int(time.time())
        time_range.end = int(time.time()) + alert_data.get('duration', 3600)  # Default 1 hour if not specified
        
        # Add affected entities
        if 'affected_entities' in alert_data:
            for entity_id in alert_data['affected_entities']:
                informed_entity = alert.informed_entity.add()
                informed_entity.route_id = entity_id
        else:
            # Add a default entity
            informed_entity = alert.informed_entity.add()
            informed_entity.route_id = "all_routes"
        
        # Set cause and effect (using enum values)
        alert.cause = alert_data.get('cause', 1)  # UNKNOWN_CAUSE
        alert.effect = alert_data.get('effect', 8)  # UNKNOWN_EFFECT

        return feed_message

    def save_protobuf(self, feed_message, message_type):
        """Save protobuf message to file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{message_type}_{timestamp}.pb"
        
        # Create type-specific directory path
        type_dir = os.path.join(self.output_dir, message_type + 's')
        os.makedirs(type_dir, exist_ok=True)
        
        filepath = os.path.join(type_dir, filename)
        
        with open(filepath, 'wb') as f:
            f.write(feed_message.SerializeToString())
        logger.info(f"Saved {message_type} to {filepath}")

    def process_data(self):
        """Process GPS and GTFS data and generate protobuf feeds"""
        try:
            # Fetch data
            gps_data = self.fetch_gps_data()
            gtfs_data = self.fetch_gtfs_static()

            if not gps_data or not gtfs_data:
                logger.error("Failed to fetch required data")
                return

            # Get vehicle information from config
            vehicle_number = gps_data.get('device_id')
            vehicle_info = self.get_vehicle_info(vehicle_number)
            
            if not vehicle_info:
                logger.error(f"No configuration found for vehicle {vehicle_number}")
                return

            # Get route and trip information from config
            route_id = str(gps_data.get('route_id'))
            logger.info(f"Looking for route {route_id} in vehicle {vehicle_number}")
            
            # Check if route exists in vehicle's routes
            if route_id in vehicle_info.get('routes', {}):
                route_info = vehicle_info['routes'][route_id]
                logger.info(f"Found route {route_id} with trips: {route_info.get('trips', [])}")
                
                # Get the current trip based on time
                current_time = datetime.now().strftime("%H:%M:%S")
                logger.info(f"Current time: {current_time}")
                
                current_trip = None
                for trip in route_info.get('trips', []):
                    trip_start_time = trip.get('start_time', '')
                    logger.info(f"Comparing trip start time {trip_start_time} with current time {current_time}")
                    if trip_start_time <= current_time:
                        current_trip = trip
                    else:
                        break
                
                if current_trip:
                    trip_id = current_trip['trip_id']
                    direction_id = current_trip['direction_id']
                    logger.info(f"Selected trip {trip_id} with direction {direction_id}")
                else:
                    # If no trip is found based on time, use the first trip
                    if route_info.get('trips', []):
                        current_trip = route_info['trips'][0]
                        trip_id = current_trip['trip_id']
                        direction_id = current_trip['direction_id']
                        logger.info(f"No time-based trip found, using first trip: {trip_id}")
                    else:
                        logger.error(f"No trips found for route {route_id}")
                        return
            else:
                logger.error(f"No route information found for route {route_id} in vehicle {vehicle_number}")
                logger.info(f"Available routes: {list(vehicle_info.get('routes', {}).keys())}")
                return

            # Update GPS data with configuration
            gps_data.update({
                'device_id': vehicle_info['device_id'],
                'label': vehicle_info['label'],
                'trip_id': trip_id,
                'route_id': route_id,
                'direction_id': direction_id
            })
            
            logger.info(f"Updated GPS data: {gps_data}")

            # Create and save vehicle position
            vehicle_position = self.create_vehicle_position(gps_data)
            self.save_protobuf(vehicle_position, 'vehicle_position')

            # Create and save trip update
            trip_update = self.create_trip_update(gps_data, gtfs_data)
            self.save_protobuf(trip_update, 'trip_update')

            # Process service alerts if any
            if 'alerts' in gtfs_data:
                for alert in gtfs_data['alerts']:
                    service_alert = self.create_service_alert(alert)
                    self.save_protobuf(service_alert, 'service_alert')

        except Exception as e:
            logger.error(f"Error processing data: {e}")
            raise

def main():
    avl_system = AVLSystem()
    
    # Schedule the processing to run every 30 seconds
    schedule.every(30).seconds.do(avl_system.process_data)
    
    logger.info("AVL System started")
    
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main() 
