#!/usr/bin/env python3

import os
import subprocess
import json
from datetime import datetime

# --- Configuration ---
# Moved API key file path to a more general config directory
API_KEY_FILE = "config/api_keys.json"
DATA_SCRIPT = "code/fetch_binance_data.sh"
LOG_DIR = "logs"

def ensure_dir(dir_path):
    """Ensures a directory exists, creating it if necessary."""
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
        print(f"Created directory: {dir_path}")

def load_api_keys(file_path=API_KEY_FILE):
    """Loads API keys from a JSON file."""
    ensure_dir(os.path.dirname(file_path))
    if not os.path.exists(file_path):
        print(f"Error: API key file not found at {file_path}")
        print("Please create it with your Binance API key and secret.")
        # Create a placeholder file with dummy keys
        with open(file_path, 'w') as f:
            json.dump({
                "binance_api_key": "YOUR_BINANCE_API_KEY",
                "binance_api_secret": "YOUR_BINANCE_API_SECRET"
            }, f, indent=4)
        print(f"Created a placeholder file at {file_path}. Please replace the dummy keys with your actual credentials.")
        return None, None

    try:
        with open(file_path, 'r') as f:
            keys = json.load(f)
        api_key = keys.get('binance_api_key')
        api_secret = keys.get('binance_api_secret')
        if not api_key or not api_secret or api_key == "YOUR_BINANCE_API_KEY":
            print(f"Warning: API keys in {file_path} are missing or are placeholder values.")
            print("Please update the file with your actual Binance API credentials.")
            # Return None to indicate that actual keys are not configured
            return None, None
        return api_key, api_secret
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {file_path}")
        return None, None
    except Exception as e:
        print(f"An unexpected error occurred while loading API keys: {e}")
        return None, None

def run_data_fetch(symbol, interval, limit):
    """Executes the shell script to fetch data from Binance."""
    api_key, api_secret = load_api_keys()

    if not api_key or not api_secret:
        print("API keys not configured. Cannot proceed with authenticated Binance API calls.")
        print("Using unauthenticated endpoints where possible.")
        # If keys are not configured, the shell script will use public endpoints.
        # For klines, this is usually fine as it's a public endpoint.
        # If you need authenticated endpoints, you MUST configure api_keys.json.

    # Ensure the data script is executable
    if os.path.exists(DATA_SCRIPT):
        os.chmod(DATA_SCRIPT, 0o755) # rwxr-xr-x
    else:
        print(f"Error: Data fetch script not found at {DATA_SCRIPT}")
        return None

    command = ["bash", DATA_SCRIPT, symbol, interval, str(limit)]
    
    try:
        # Execute the command. Capturing output for processing.
        process = subprocess.run(command, capture_output=True, text=True, check=True)
        log_file_path = os.path.join(LOG_DIR, f"fetch_{symbol.lower()}_{interval}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        ensure_dir(LOG_DIR)
        with open(log_file_path, 'w') as log_file:
            log_file.write(f"Command: {' '.join(command)}\n\n")
            log_file.write(f"STDOUT:\n{process.stdout}\n\n")
            log_file.write(f"STDERR:\n{process.stderr}\n")

        print(f"Successfully fetched data for {symbol}. Output logged to {log_file_path}")
        
        # Process the JSON output from the script (assuming stdout is JSON)
        data = json.loads(process.stdout)
        return data

    except subprocess.CalledProcessError as e:
        error_log_path = os.path.join(LOG_DIR, f"error_{symbol.lower()}_{interval}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        ensure_dir(LOG_DIR)
        with open(error_log_path, 'w') as error_file:
            error_file.write(f"Command: {' '.join(command)}\n\n")
            error_file.write(f"Return Code: {e.returncode}\n\n")
            error_file.write(f"STDOUT:\n{e.stdout}\n\n")
            error_file.write(f"STDERR:\n{e.stderr}\n")
        print(f"Error executing data fetch script: {e}. Full error logged to {error_log_path}")
        return None
    except json.JSONDecodeError:
        error_log_path = os.path.join(LOG_DIR, f"json_error_{symbol.lower()}_{interval}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        ensure_dir(LOG_DIR)
        with open(error_log_path, 'w') as error_file:
            error_file.write(f"Command: {' '.join(command)}\n\n")
            error_file.write(f"STDOUT:\n{process.stdout}\n\n") # process might not be defined here if error happened before it
            error_file.write(f"STDERR:\n{e.stderr}\n") # e might not be defined
        print("Error: Could not decode JSON response from the script.")
        print(f"Raw output (if available): {process.stdout if 'process' in locals() else 'N/A'}")
        print(f"JSON decoding error logged to {error_log_path}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during data fetching: {e}")
        return None

if __name__ == "__main__":
    # --- Example Usage ---
    # This part demonstrates how to use the functions.
    # In a production environment, this would be called by the main script or framework.
    
    print("--- Data Management Script ---")

    # Ensure necessary directories and files exist
    ensure_dir(os.path.dirname(API_KEY_FILE))
    ensure_dir(DATA_SCRIPT.split('/')[0]) # Ensure the code directory exists
    ensure_dir(LOG_DIR)

    # Load API keys (will create a placeholder if not found)
    api_key, api_secret = load_api_keys()
    if api_key and api_secret:
        print("API keys loaded successfully.")
    else:
        print("Proceeding with placeholder/unauthenticated API access.")

    # Make the data fetch script executable if it exists
    if os.path.exists(DATA_SCRIPT):
        os.chmod(DATA_SCRIPT, 0o755) # rwxr-xr-x
        print(f"Made {DATA_SCRIPT} executable.")
    else:
        print(f"Warning: Data fetch script '{DATA_SCRIPT}' not found. Cannot execute.")
        # Exit if the script is essential and not found
        # exit(1) 

    print("\n--- Running Data Acquisition Example ---")
    symbol = "BTCUSDT"
    interval = "1h"
    limit = 100

    fetched_data = run_data_fetch(symbol, interval, limit)

    if fetched_data is not None:
        print(f"\nData acquisition process completed.")
        if isinstance(fetched_data, list) and len(fetched_data) > 0:
            print(f"Successfully fetched {len(fetched_data)} data points for {symbol}.")
            # Example: Print the first data point (assuming it's a list of lists/dicts)
            if fetched_data and isinstance(fetched_data[0], (list, dict)):
                 print("First data point:", fetched_data[0])
            else:
                print("Fetched data is not in the expected list format or is empty.")
        elif isinstance(fetched_data, dict) and fetched_data:
            print(f"Successfully fetched data for {symbol}. Raw response:")
            print(fetched_data)
        else:
            print("No data was returned or the data format is unexpected.")
    else:
        print("\nData acquisition process failed.")
