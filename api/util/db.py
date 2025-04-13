from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import pandas as pd
import numpy as np
import decimal
from datetime import datetime, date

field_map = {
    "cashandcashequivalents": "cashandcashequivalentsatcarryingvalue",
    "cogs": "costofgoodsandservicessold",
    "totalrevenue": "totalrevenue",
    "costofrevenue": "costofrevenue",
    "grossprofit": "grossprofit",
    "operatingexpense": "operatingexpense",
    "ebit": "ebit",
    "ebitda": "ebitda",
    "depreciation": "depreciation",
    "interestincome": "interestincome",
    "interestexpense": "interestexpense",
    "netincome": "netincome",
    "totalassets": "totalassets",
    "totalliabilities": "totalliabilities",
    "totalshareholderequity": "totalshareholderequity",
    "goodwill": "goodwill",
    "inventory": "inventory",
    "capitalexpenditures": "capitalexpenditures",
    "operatingcashflow": "operatingcashflow"
}



db = SQLAlchemy()

def init_app(app):
    """Initialize the database with the Flask app"""
    db.init_app(app)


# Takes a ticker and a date range and returns the stock price for that ticker (close price on daily time interval)
def query_price(ticker, start_date, end_date, interval='daily'):
    ticker = ticker.upper()
    sql = f"SELECT date, close FROM stock_prices WHERE ticker = :ticker AND date >= :start_date AND date <= :end_date ORDER BY date ASC"
    params = {"ticker": ticker}
    params["start_date"] = datetime(int(start_date), 1, 1)
    params["end_date"] = datetime(int(end_date), 12, 31)

    result = db.session.execute(text(sql), params)
    df = pd.DataFrame(result.fetchall(), columns=result.keys())
    df['date'] = pd.to_datetime(df['date']) # TODO :: check if this is needed, does sqlalchemy already convert to datetime?
    df.set_index('date', inplace=True)
    df.sort_index(inplace=True) # if data is already sorted, which it should be if nothing goes wrong, then this will add basically 0 overhead

    return df


    result_proxy = db.session.execute(text(sql), params)
    
    result = parse_output(result_proxy, 'date')
    print("\nStock price result: ", result)
    return result


# Takes a ticker and a list of metrics and returns the financial data for that ticker
def query_financials(ticker, metrics, start_date=None, end_date=None):
    if 'stockprice' in metrics:
        metrics.remove('stockprice')
        stock_price = query_price(ticker, start_date, end_date)

    cols = [field_map[m] for m in metrics if m in field_map]
    
    cols.insert(0, "fiscaldateending")
    
    sql = f"SELECT {', '.join(cols)} FROM financials WHERE ticker = :ticker"
    params = {"ticker": ticker}

    # TODO if start_date/end_date is None, set it to some default values. maybe -10 years to present day?
    if start_date is not None:
        sql += f" AND fiscaldateending >= :start_date"
        params["start_date"] = datetime(int(start_date), 1, 1)
    
    if end_date is not None:
        sql += f" AND fiscaldateending <= :end_date"
        params["end_date"] = datetime(int(end_date), 12, 31)
    
    sql += " ORDER BY fiscaldateending DESC"

    result = db.session.execute(text(sql), params)
    financials = pd.DataFrame(result.fetchall(), columns=result.keys())
    financials['fiscaldateending'] = pd.to_datetime(financials['fiscaldateending'])
    financials = financials.rename(columns={'fiscaldateending': 'date'})
    financials.set_index('date', inplace=True)
    financials.sort_index(inplace=True) # if data is already sorted, which it should be if nothing goes wrong, then this will add basically 0 overhead
    return pd.concat([financials, stock_price], axis=1)

    result_proxy = db.session.execute(text(sql), params)
    
    result = parse_output(result_proxy, 'fiscaldateending')
    print("\nFinancials result: ", result)
    return result

    
# Takes a SQLAlchemy result proxy and converts it to a dictionary of dictionaries, with key_field as the key for the outer dictionary
def parse_output(result_proxy, key_field):
    # Convert column names to a list so we can use index()
    column_names = list(result_proxy.keys())
    print("\n\nColumn names: ", column_names)
    
    # Find the index of your key_field in the column names
    key_field_index = column_names.index(key_field)
    print("Key field index: ", key_field_index)

    result = {}
    for row in result_proxy:
        print("Row: ", row)
        # Get the key value using the index
        raw_key = row[key_field_index]
        
        # Convert the key to a string if it's a date/datetime
        if isinstance(raw_key, (date, datetime)):
            key = raw_key.isoformat()
        else:
            key = raw_key
            
        if key not in result:
            result[key] = {}
            
        # Process each column
        for i, column in enumerate(column_names):
            if column != key_field:
                value = row[i]
                if isinstance(value, decimal.Decimal):
                    value = float(value)
                elif isinstance(value, (datetime, date)):
                    value = value.isoformat()
                result[key][column] = value
                
    return result