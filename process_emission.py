import os
import csv
import json
import logging
import sys
import time
from typing import Dict, List, Union, Optional

# Get absolute path to data folder - CORRECTED PATH
current_dir = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(current_dir, '.aws_iot_resources', 'data')

try:
    import greengrasssdk
    client = greengrasssdk.client("iot-data")
    GG_ENV = True
except ImportError:
    GG_ENV = False
    print("Running in local test mode (no Greengrass SDK)")

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

def load_vehicle_data(vehicle_id: str) -> List[Dict]:
    """Load and process vehicle data from CSV files"""
    vehicle_data = []
    file_path = os.path.join(DATA_PATH, f"{vehicle_id}.csv")
    
    if not os.path.exists(file_path):
        logger.error(f"Data file not found: {file_path}")
        return vehicle_data

    try:
        with open(file_path, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Convert numeric values and clean the data
                processed = {}
                for key, value in row.items():
                    try:
                        # Handle empty strings and convert numbers
                        if value.strip() == '':
                            processed[key] = 0.0
                        else:
                            processed[key] = float(value)
                    except (ValueError, AttributeError):
                        processed[key] = value.strip()
                vehicle_data.append(processed)
                
        logger.info(f"Loaded {len(vehicle_data)} records from {vehicle_id}.csv")
        
    except Exception as e:
        logger.error(f"Error processing {file_path}: {str(e)}")
    
    return vehicle_data

def process_emission_data(records: Union[str, Dict, List]) -> Optional[Dict]:
    """Process vehicle data to find maximum CO2 emission"""
    max_co2 = 0.0
    vehicle_id = None
    valid_records = 0

    # Handle vehicle_id string input
    if isinstance(records, str):
        records = load_vehicle_data(records)

    # Normalize input format
    if not isinstance(records, list):
        records = [records] if isinstance(records, dict) else []

    if not records:
        logger.error("No valid records found")
        return None

    for record in records:
        try:
            # Get CO2 value - using the exact field name from your CSV
            co2_val = record['vehicle_CO2']  # This matches your CSV header
            
            # Get vehicle ID - also matches your CSV
            current_vehicle_id = record['vehicle_id']
            
            # Initialize or verify consistent vehicle_id
            if vehicle_id is None:
                vehicle_id = current_vehicle_id
            elif vehicle_id != current_vehicle_id:
                logger.warning(f"Ignoring record for different vehicle: {current_vehicle_id}")
                continue

            # Track maximum CO2 value
            if co2_val > max_co2:
                max_co2 = co2_val
                
            valid_records += 1
                
        except (KeyError, TypeError, ValueError) as e:
            logger.warning(f"Skipping invalid record: {str(e)}")
            continue

    if not valid_records:
        logger.error("No valid CO2 measurements found")
        return None

    logger.info(f"Processed {valid_records} records for {vehicle_id}, max CO2: {max_co2}")
    
    return {
        "vehicle_id": vehicle_id,
        "max_co2": max_co2,
        "timestamp": int(time.time()),
        "unit": "ppm",
        "records_processed": valid_records
    }

def lambda_handler(event, context=None):
    """Handler for AWS Lambda/Greengrass"""
    result = process_emission_data(event)
    if result and GG_ENV:
        publish_results(result)
    return result

def publish_results(result: Dict) -> bool:
    """Publish results to IoT Core"""
    try:
        topic = f"vehicles/{result['vehicle_id']}/emission/results"
        client.publish(
            topic=topic,
            payload=json.dumps(result)
        )
        logger.info(f"Published to {topic}: {result}")
        return True
    except Exception as e:
        logger.error(f"Publish failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("\nVehicle Emission Processor")
    print(f"Data directory: {DATA_PATH}")
    
    try:
        # Check if data directory exists
        if not os.path.exists(DATA_PATH):
            raise FileNotFoundError(f"Directory not found: {DATA_PATH}")
        
        # Find all vehicle CSV files
        vehicle_files = [
            f for f in os.listdir(DATA_PATH) 
            if f.startswith('vehicle') and f.endswith('.csv')
        ]
        
        if not vehicle_files:
            raise FileNotFoundError("No vehicle CSV files found")
        
        print(f"\nFound {len(vehicle_files)} vehicle files:")
        for f in sorted(vehicle_files):
            print(f"- {f}")
        
        # Process each vehicle file
        for csv_file in sorted(vehicle_files):
            vehicle_id = os.path.splitext(csv_file)[0]
            print(f"\nProcessing {vehicle_id}...")
            
            result = process_emission_data(vehicle_id)
            if result:
                print(f"Results:")
                print(f"- Vehicle ID: {result['vehicle_id']}")
                print(f"- Max CO2: {result['max_co2']} ppm")
                print(f"- Records processed: {result['records_processed']}")
                
                if GG_ENV:
                    if publish_results(result):
                        print("Published to IoT Core")
            else:
                print(f"Failed to process {vehicle_id}")
                
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        print("\nTroubleshooting steps:")
        print(f"1. Verify the folder exists: {DATA_PATH}")
        print("2. Ensure it contains vehicle CSV files (vehicle0.csv, vehicle1.csv, etc.)")
        print("3. Check file permissions")
        print("4. Confirm CSV files have 'vehicle_CO2' and 'vehicle_id' columns")
        sys.exit(1)