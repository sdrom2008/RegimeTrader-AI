#!/bin/bash

# This script processes JSON data files into CSV format.

INPUT_DIR="data/new_fetch"
OUTPUT_DIR="data/csv"

# Create output directory if it doesn't exist
mkdir -p ${OUTPUT_DIR}

echo "Starting JSON to CSV processing..."

# Check if jq is installed
if ! command -v jq &> /dev/null
then
    echo "jq could not be found. Please install jq (e.g., sudo apt-get install jq) to process JSON files."
    exit 1
fi

# Process each JSON file in the input directory
for json_file in ${INPUT_DIR}/*.json; do
    if [ -f "$json_file" ]; then
        filename=$(basename -- "$json_file")
        base_filename="${filename%.*}" # Remove .json extension
        csv_file="${OUTPUT_DIR}/${base_filename}.csv"

        echo "Processing ${json_file} to ${csv_file}..."

        # Binance klines JSON structure:
        # [ [open_time, open, high, low, close, volume, close_time, quote_asset_volume, number_of_trades, taker_buy_base_asset_volume, taker_buy_quote_asset_volume, ignore], ... ]
        # We want to extract: Open time, Open, High, Low, Close, Volume.
        # Format: timestamp,open,high,low,close,volume

        jq -r '.[] as $row | $row | @csv' "$json_file" > "$csv_file"
        
        # Add header to CSV file (optional, but good practice)
        echo "timestamp,open,high,low,close,volume" | cat - "$csv_file" > temp_csv && mv temp_csv "$csv_file"
        
        if [ $? -eq 0 ]; then
            echo "Successfully processed ${json_file} to ${csv_file}"
        else
            echo "Error processing ${json_file}."
        fi
    fi
done

echo "JSON to CSV processing completed."

exit 0
