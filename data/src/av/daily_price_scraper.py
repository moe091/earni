#!/usr/bin/env python3
import av_helpers as ah
import psycopg2  # You can replace with your preferred DB connector
import datetime
import logging
import time
from decimal import Decimal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='stock_import.log'
)

# Database connection parameters - update these with your actual values
DB_PARAMS = {
    'dbname': 'earni',
    'user': 'earni',
    'password': '10Mojo17!',
    'host': 'localhost',
    'port': '5432'
}

def connect_to_db():
    """Establish a connection to the database."""
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        return conn
    except Exception as e:
        logging.error(f"Database connection error: {e}")
        raise

def read_ticker_list(filename):
    """Read ticker symbols from the provided file."""
    try:
        with open(filename, 'r') as f:
            # Strip whitespace and filter out empty lines
            tickers = [line.strip().upper() for line in f if line.strip()]
        logging.info(f"Loaded {len(tickers)} tickers from {filename}")
        return tickers
    except Exception as e:
        logging.error(f"Error reading ticker list: {e}")
        raise

def process_ticker(ticker, conn, min_date=None):
    """Process a single ticker and add its data to the database."""
    try:
        logging.info(f"Retrieving data for {ticker}")
        
        # Get all daily data for the ticker
        ticker_data = ah.get_daily(ticker)
        
        if not ticker_data:
            logging.warning(f"No data returned for {ticker}")
            return 0
        
        # Filter for dates >= min_date
        if min_date:
            ticker_data = {date: data for date, data in ticker_data.items() 
                          if date >= min_date}
        
        # Insert data into the database
        cursor = conn.cursor()
        count = 0
        
        for date, data in ticker_data.items():
            try:
                # Skip if missing required data
                if not all(key in data for key in ['1. open', '2. high', '3. low', '4. close', '5. volume']):
                    logging.warning(f"Incomplete data for {ticker} on {date}")
                    continue
                
                # Map values to the appropriate types
                open_price = Decimal(data['1. open'])
                high_price = Decimal(data['2. high'])
                low_price = Decimal(data['3. low'])
                close_price = Decimal(data['4. close'])
                volume = int(data['5. volume'])
                
                # SQL for insert with conflict handling
                sql = """
                INSERT INTO stock_prices 
                (ticker, date, open, high, low, close, volume)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (ticker, date) DO UPDATE SET
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume
                """
                
                cursor.execute(sql, (
                    ticker, date, open_price, high_price, low_price, 
                    close_price, volume
                ))
                count += 1
                
                # Commit every 100 inserts to avoid large transactions
                if count % 100 == 0:
                    conn.commit()
                    
            except Exception as e:
                logging.error(f"Error inserting {ticker} data for {date}: {e}")
                # Continue with other dates
        
        # Final commit for this ticker
        conn.commit()
        cursor.close()
        
        logging.info(f"Inserted/updated {count} records for {ticker}")
        return count
        
    except Exception as e:
        logging.error(f"Error processing ticker {ticker}: {e}")
        return 0

def main():
    """Main function to orchestrate the data import process."""
    start_time = time.time()
    min_date = "2010-01-01"  # Starting from 2010 as requested
    
    try:
        # Read ticker list
        tickers = read_ticker_list('tickerlist.txt')
        
        # Connect to database
        conn = connect_to_db()
        
        total_records = 0
        success_count = 0
        
        # Process each ticker
        for i, ticker in enumerate(tickers):
            try:
                records = process_ticker(ticker, conn, min_date)
                total_records += records
                if records > 0:
                    success_count += 1
                
                # Add delay to avoid overwhelming API
                if i < len(tickers) - 1:
                    time.sleep(1)  # 1 second delay between requests
                    
            except Exception as e:
                logging.error(f"Failed to process {ticker}: {e}")
                # Continue with next ticker
                
        # Log summary
        elapsed_time = time.time() - start_time
        logging.info(f"Import completed in {elapsed_time:.2f} seconds")
        logging.info(f"Successfully processed {success_count}/{len(tickers)} tickers")
        logging.info(f"Total records imported: {total_records}")
        
        conn.close()
        
    except Exception as e:
        logging.critical(f"Critical error in main process: {e}")
        raise

if __name__ == "__main__":
    main()