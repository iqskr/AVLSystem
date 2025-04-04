# AVL System with GPSLogger and GTFS Integration

This system integrates GPSLogger application data with GTFS feeds to generate GTFS-realtime protobuf messages for vehicle positions, trip updates, and service alerts.

## Features

- Real-time vehicle position tracking
- Trip updates based on GPS data and GTFS schedule
- Service alerts generation
- Protobuf output generation
- Configurable update intervals

## Prerequisites

- Python 3.8 or higher
- GPSLogger application running and accessible
- GTFS static feed URL
- Internet connection for data fetching

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd avl-system
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy the example environment file and configure it:
```bash
cp .env.example .env
```

5. Edit the `.env` file with your configuration:
- Set `GPS_LOGGER_URL` to your GPSLogger application's API endpoint
- Set `GTFS_STATIC_URL` to your GTFS static feed URL
- Optionally modify `OUTPUT_DIR` if you want to change the output location

## Usage

1. Start the AVL system:
```bash
python avl_system.py
```

The system will:
- Fetch GPS data from GPSLogger every 30 seconds
- Fetch GTFS static data
- Generate and save protobuf messages for:
  - Vehicle positions
  - Trip updates
  - Service alerts (if any)

2. The generated protobuf files will be saved in the configured output directory with timestamps in the filename.

## Output Files

The system generates three types of protobuf files:
- `vehicle_position_YYYYMMDD_HHMMSS.pb`: Contains real-time vehicle position data
- `trip_update_YYYYMMDD_HHMMSS.pb`: Contains trip updates and estimated arrival times
- `service_alert_YYYYMMDD_HHMMSS.pb`: Contains service alerts (if any)

## Error Handling

The system includes comprehensive error handling and logging:
- Failed API requests are logged
- Data processing errors are logged
- File writing errors are logged

All logs are printed to the console with timestamps and log levels.

## Contributing

Feel free to submit issues and enhancement requests! 