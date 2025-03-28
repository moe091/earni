import requests
import psycopg2
from psycopg2 import sql
av_url = 'https://www.alphavantage.co/query?function=%s&symbol=%s&apikey=6Q3GY2NWGVNBQKHE'
conn = None


def get_stock_data(ticker, func):
    url = av_url % (func, ticker)
    print("Requesting URL: ", url)
    r = requests.get(url)
    data = r.json()

    return data


def populate_ticker(ticker):
    data = get_stock_data(ticker, "INCOME_STATEMENT")
    try:
        for r in data['annualReports']:
            upsert_financials("yearly_financials", ticker, r)
            
        for r in data['quarterlyReports']:
            upsert_financials("financials", ticker, r)
    except KeyError:
        print(f"Keyerror for ticker {ticker}", data)
        raise

    
def upsert_financials(table_name, ticker, data):
    o = {}
    o['ticker'] = ticker
    for k, v in data.items():
        if v != 'None': # av returns JSON where null values are the string 'None'
            o[k.lower()] = v

    return upsert(table_name, o, ['ticker', 'fiscaldateending'])

def upsert(table_name, data, primary_keys):
    conn = get_conn()
    if not data or not primary_keys:
        raise ValueError("Data and primary keys must be provided")
    
    # Make sure primary keys are present in the data
    for key in primary_keys:
        if key not in data:
            raise ValueError(f"Primary key '{key}' must be present in the data")
    
    # Get table columns to validate keys in data
    with conn.cursor() as cursor:
        cursor.execute(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = %s
        """, (table_name,))
        valid_columns = [row[0] for row in cursor.fetchall()]
    
    # Filter data to only include valid columns
    filtered_data = {k: v for k, v in data.items() if k in valid_columns}
    
    # If no valid columns remain after filtering, raise an error
    if not filtered_data:
        raise ValueError("No valid columns found in the provided data")
    
    # Prepare column names and placeholders
    columns = filtered_data.keys()
    
    # Create a list of column=value for the update part
    # Exclude primary key columns from update operation
    update_parts = [f"{col} = EXCLUDED.{col}" for col in columns if col not in primary_keys]
    
    # Construct the query
    query = sql.SQL("""
        INSERT INTO {table} ({columns})
        VALUES ({values})
        ON CONFLICT ({pk_columns}) 
        DO UPDATE SET {update_set}
    """).format(
        table=sql.Identifier(table_name),
        columns=sql.SQL(', ').join(map(sql.Identifier, columns)),
        values=sql.SQL(', ').join(sql.Placeholder(name) for name in columns),
        pk_columns=sql.SQL(', ').join(map(sql.Identifier, primary_keys)),
        update_set=sql.SQL(', ').join(map(sql.SQL, update_parts)) if update_parts else sql.SQL("(SELECT NULL WHERE FALSE)")
    )
    
    # Execute the query
    with conn.cursor() as cursor:
        cursor.execute(query, filtered_data)
    
    conn.commit()





def get_conn():
    """
    This method creates a connection to the database, or returns one if it already exists.

    Returns:
        psycopg2.connection: A connection to the database.
    """

    global conn
    if conn is not None:
        return conn
    
    # grab database password from file
    dbpassword = '10Mojo17!'

    # create database connection
    try:
        conn = psycopg2.connect(f"dbname='earni' user='earni' host='localhost' password='{dbpassword}'")
        print("Connected to earni database", True)
    except Exception as e:
        print("Failed to connect to database")
        raise e

    return conn

# Example usage
if __name__ == "__main__":
    # Example ticker symbol
    ticker = "AAPL"
    
    # Example list of dates
    sample_dates = [
        datetime.date(2024, 3, 1),
        datetime.date(2024, 3, 4),
        datetime.date(2024, 3, 5)
    ]
    
    # Get the stock data
    result_data = get_stock_data(ticker, sample_dates)
    
    # Display the results
    print(f"Stock data for {ticker}:")
    print(result_data)