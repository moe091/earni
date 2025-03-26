import schema as sc
import edgar2 as ed
import database as db
import time
import random
import traceback

schema = sc.financial_metrics
MAX_RETRIES = 5  # Maximum number of retries

def update_ticker(ticker):
    retries = 0
    success = False
    
    while not success and retries <= MAX_RETRIES:
        try:
            print(f"Scraping data for {ticker} (Attempt {retries + 1})")
            
            # Create EdgarInstance with retry logic
            edgar = ed.EdgarInstance(ticker)
            data = edgar.populate_schema(schema)
            
            # Process data if we got this far
            for k, v in data.items():
                print(f"\n\nUpdating {ticker} - {k}:")
                for prop, val in v.items():
                    print(f"{prop}: {val}")
                
                # Add original_report_date if it doesn't exist
                if 'original_report_date' not in v:
                    # Assume it doesn't have the field and use a default date format
                    month, year = k.split("/")
                    v['original_report_date'] = f"{year}-{month.zfill(2)}-01"
                
                db.update_financial_data(ticker, k, v.get('original_report_date'), v)
            
            # If we get here, it worked!
            success = True
            print(f"Successfully processed {ticker}")
            
        except Exception as e:
            retries += 1
            
            # Log the error
            print(f"Error processing {ticker} (Attempt {retries}/{MAX_RETRIES}): {str(e)}")
            print(traceback.format_exc())
            
            if retries <= MAX_RETRIES:
                # Exponential backoff
                wait_time = 2 ** retries + random.uniform(0, 1)
                print(f"Retrying in {wait_time:.2f} seconds...")
                time.sleep(wait_time)
            else:
                print(f"Max retries exceeded for {ticker}. Moving to next ticker.")
    
    return success

if __name__ == "__main__":
    with open("./tickerlist.txt", "r") as file:
        lines = file.readlines()
    
    while len(lines) > 0:
        ticker = lines.pop(0).strip()
        success = update_ticker(ticker)
        
        # If it failed after all retries, add to failed list
        if not success:
            with open("./failed_tickers.txt", "a") as file:
                file.write(f"{ticker}\n")
            print(f"Wrote {ticker} failed tickers to failed_tickers.txt")
        
        # Write remaining tickers back to file
        with open("./tickerlist.txt", "w") as file:
            for l in lines:
                file.write(l)

