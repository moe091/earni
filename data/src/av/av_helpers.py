import requests
av_url = 'https://www.alphavantage.co/query?function=%s&symbol=%s&apikey=6Q3GY2NWGVNBQKHE'


def get_data(ticker, func):
    url = av_url % (func, ticker)
    r = requests.get(url)
    data = r.json()

    return data

def get_income(ticker):
    url = av_url % ("INCOME_STATEMENT", ticker)
    r = requests.get(url)
    return r.json()

def get_balance_sheet(ticker):
    url = av_url % ("BALANCE_SHEET", ticker)
    r = requests.get(url)
    return r.json()

def get_cash_flow(ticker):
    url = av_url % ("CASH_FLOW", ticker)
    r = requests.get(url)
    return r.json()

def get_daily(ticker):
    url = av_url % ("TIME_SERIES_DAILY", ticker) + "&outputsize=full&datatype=json"
    r = requests.get(url)
    return r.json()