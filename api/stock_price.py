import pandas as pd
import datetime
import yfinance as tf
import requests
av_url = 'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol=amd&apikey=G3BQN2GJIA27GHCE'

def get_stock_data(ticker, func):
    url = "https://www.alphavantage.co/query?function=" + func + "&symbol=" + ticker + "&apikey=G3BQN2GJIA27GHCE"
    r = requests.get(url)
    data = r.json()

    return data

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