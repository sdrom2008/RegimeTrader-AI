#!/bin/bash

# This script fetches historical crypto data from Binance.

SYMBOL1="ADAUSDT"
SYMBOL2="BNBUSDT"
TIMEFRAME="15m" # 15-minute K-line data
LIMIT="500"   # Number of data points to fetch (reduced for shorter interval)

OUTPUT_DIR="data/new_fetch" # Directory to save the fetched data

# Create output directory if it doesn't exist
mkdir -p ${OUTPUT_DIR}

echo "Starting data fetch for ${SYMBOL1} and ${SYMBOL2}..."

# Fetch data for SYMBOL1
echo "Fetching ${SYMBOL1} data (${TIMEFRAME}, limit=${LIMIT})..."
curl -s -G https://api.binance.com/api/v3/klines --data-urlencode "symbol=${SYMBOL1}" --data-urlencode "interval=${TIMEFRAME}" --data-urlencode "limit=${LIMIT}" > ${OUTPUT_DIR}/${SYMBOL1}_${TIMEFRAME}.json
if [ $? -eq 0 ]; then
    echo "Successfully fetched ${SYMBOL1} data to ${OUTPUT_DIR}/${SYMBOL1}_${TIMEFRAME}.json"
else
    echo "Error fetching ${SYMBOL1} data."
fi

# Fetch data for SYMBOL2
echo "Fetching ${SYMBOL2} data (${TIMEFRAME}, limit=${LIMIT})..."
curl -s -G https://api.binance.com/api/v3/klines --data-urlencode "symbol=${SYMBOL2}" --data-urlencode "interval=${TIMEFRAME}" --data-urlencode "limit=${LIMIT}" > ${OUTPUT_DIR}/${SYMBOL2}_${TIMEFRAME}.json
if [ $? -eq 0 ]; then
    echo "Successfully fetched ${SYMBOL2} data to ${OUTPUT_DIR}/${SYMBOL2}_${TIMEFRAME}.json"
else
    echo "Error fetching ${SYMBOL2} data."
fi

echo "Data fetching process completed."
# Removed echo "Next steps: Process JSON files to CSV format."

exit 0
