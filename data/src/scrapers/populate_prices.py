import yfinance as yf
import psycopg2 as pg2
import pandas as pd
import pandas_market_calendars as mcal
import traceback
import sys
import os
from datetime import date, timedelta

sys.path.append(os.path.abspath(os.path.join(os.getcwd(), '..')))
import database as db

nyse = mcal.get_calendar("NYSE")
query = None



def get_dates_for_ticker(ticker):
    """
    This method retrieves a list of all the tickers in the database.

    Returns:
        list: A list of all the tickers in the database.
    """

    conn = db.get_conn() # returns existing db connection, or creates one if needed

    with conn.cursor() as curs:
        try:
            curs.execute(f"SELECT ticker, date, time_of_report FROM earnings_reports WHERE ticker = '{ticker}'")
            dates = curs.fetchall()
        except Exception as e:
            print(f"Failed to get dates from database for ticker {ticker}", traceback.format_exc())
            raise e

    print(f"Retrieved {len(dates)} dates for ticker {ticker}")

    return dates


def find_relative_dates(date, offset):
    #print(f"\n\nFinding relative dates for {date}. Offset={offset}")
    if offset:
        date = date - timedelta(days=1)
    
    #print(f"new date = {date}")

    offsets = [1, 2, 3, 4, 5, 10, 20, 30]
    rel_dates = []
    end_date = date + timedelta(days=55)
    sched = nyse.schedule(start_date=date.strftime("%Y-%m-%d"), end_date=end_date.strftime("%Y-%m-%d"))
    
    for o in offsets:
        odate = sched.iloc[o].iloc[0].date()
        rel_dates.append((o, odate))

    
    #REVERSE!
    offsets = [-1, -2, -3, -4, -5, -10, -20, -30]
    start_date = date - timedelta(days=50)
    sched = nyse.schedule(start_date=start_date.strftime("%Y-%m-%d"), end_date=date.strftime("%Y-%m-%d"))

    for o in offsets:
        odate = sched.iloc[o].iloc[0].date()
        rel_dates.append((o, odate))
    
    #print(rel_dates)


    #sched[1] is the day after 'date'. For post-market this makes sense. for pre-market we set 'date' back by 1 day, so sched[1] is
    #actually the same day as the report, which is what we want because thats the first trading session 'after' the report
    
    #sched.iloc[-1].iloc[0].date() is equal to date. The [-1] element is the original date passed into this func.
    #that corresponds to the -1 offset, because if it was an after-hours report then the last day before the report
    #IS the same day. If it was a pre-market

    return rel_dates


def get_prices_for_dates(ticker, dates, report_date):
    yt = yf.Ticker(ticker)

    # yt.history end date isn't inclusive, have to increase our last date by 1 day to include it
    end_date = dates[-1][1] + timedelta(days=1)
    prices = yt.history(start=dates[0][1].strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"))
    prices.index = prices.index.map(lambda d: d.date().strftime("%Y-%m-%d"))
    price_data = []
    
    # NOTE :: I AM HERE! KeyError occurs if earnings report was less than 30 days ago because prices won't have an entry for the plus_30 values.
    # NOTE :: ALSO, there may be an error with Before Hours reports, I may have lost the -1 day adjustment I was supposed to include.
    for d in dates:
        d_string = d[1].strftime("%Y-%m-%d")
        try:
            price_point = {
                "ticker": ticker,
                "report_date": report_date,
                "offset": d[0],
                "open": int(round(prices.loc[d_string]['Open'], 2) * 100),
                "close": int(round(prices.loc[d_string]['Close'], 2) * 100),
                "high": int(round(prices.loc[d_string]['High'], 2) * 100),
                "low": int(round(prices.loc[d_string]['Low'], 2) * 100),
                "volume": int(prices.loc[d_string]['Volume'])
            }
            price_data.append(price_point)
        except:
            print(f"[Skipping PricePoint] Unable to insert pricepoint for {ticker} - {d}")
            with open("./ph_skips.txt", "w", encoding="utf-8") as file:
                file.write(f"\n[Skipping PricePoint] {ticker} - {d}\n")

    return price_data


def get_db_entry(price_data):
    entry = {}
    entry['ticker'] = price_data[0]['ticker']
    entry['report_date'] = price_data[0]['report_date']
    for p in price_data:
        if p['offset'] < 0:
            suffix = f"minus_{abs(p['offset'])}"
        else:
            suffix = f"plus_{p['offset']}"
        
        entry[f"open_{suffix}"] = p['open']
        entry[f"close_{suffix}"] = p['close']
        entry[f"high_{suffix}"] = p['high']
        entry[f"low_{suffix}"] = p['low']
        entry[f"volume_{suffix}"] = p['volume']

    print(f"[{entry['report_date']}] close_minus_1={entry['close_minus_1']}, close_plus_1={entry['close_plus_1']}")
    return entry
    
    # conn = db.get_conn()
    # with conn.cursor() as curs:
    #     for p in price_data:
    #         try:
    #             #curs.execute(f"INSERT INTO stock_prices (ticker, report_date, offset, open, close, high, low, volume) VALUES ('{p['ticker']}', '{p['report_date']}', {p['offset']}, {p['open']}, {p['close']}, {p['high']}, {p['low']}, {p['volume']})")
    #         except Exception as e:
    #             print(f"Failed to insert price data for {p['ticker']} on {p['report_date']} offset {p['offset']}", traceback.format_exc())
    #             raise e
    # conn.commit()
    # print(f"Inserted {len(price_data)} price records into the database")


def create_row(report, rel):
    """
        (realizing this func needs to be renamed... in fact, the whole structure of this script has changed and needs to be reorganized)
        Takes a single earnings report, and a list of relative dates, and retrieves necessary price data by calling
        get_prices_for_dates. Then inserts all of that data into the database by calling insert_price_data
    """
    # Some entries don't have a valid time_of_report(e.g. After Hours or Before Open). I need an is_valid field to make it easier to find or ignore these entries
    is_valid = True
    if report[2] == "Invalid":
        is_valid = False

    # sort dates so logs are easier to comprehend
    rel.sort(key=lambda d: d[0])

    # grab price data from yfinance for the relative dates
    price_data = get_prices_for_dates(report[0], rel, report[1])

    # create entry dicts with correct format for db
    entry = get_db_entry(price_data)
    entry['is_valid'] = is_valid

    # create query because I don't feel like hand writing it
    global query
    
    # recreate query each time, because some keys may be missing in some cases and will require a different query
    # this should probably be handled somewhere else but it was the last fix I noticed was necessary and it's
    # not worth refactoring since this is a 1-time script to populate DB
    query = f"""
    INSERT INTO price_history ({', '.join(entry.keys())})
    VALUES ({', '.join([f'%({key})s' for key in entry.keys()])})
    """

    return query, entry



def populate_prices(ticker):
    """
        Populates relative stock prices for all earnings report records for a given ticker
        This is the root function called which handles every step to update all records for a given ticker

        1. Retrieve all earning report dates for the ticker [get_dates_for_ticker(ticker)]
        2. for each ER date:
            3. find all relative dates for the given date(-30d, +5d, etc) [find_relative_dates(report_date)]
            4. insert stock price data(open, close, high, etc) for each relative date into DB [insert_rel_dates]:
                5. insert_rel_dates first calls get_prices_for_dates(ticker, dates) to get prices at each date
                6. then it will call insert_prices(price_data) where it inserts all prices for each date into the DB
    """
        
    dates = get_dates_for_ticker(ticker)
    # dates includes the date of each earnings report for the given ticker
    # for each date in dates, find all 'relative_dates'. 
    # add the closing price for each relative_date to the database WHERE ticker=ticker AND date=date (undo the -1 day for pre-market!)
    # column names will be minus_1_day, minus_5_day, plus_1_day, plus_30_day, etc...

    rows = []
    for d in dates:
        if d[2] != "Before Open" and d[2] != "After Close":
            print(f"[Skipping Row] Invalid time_of_report for {ticker} - {d}")
            with open("./ph_skips.txt", "w", encoding="utf-8") as file:
                file.write(f"\n[Missing Data For Row] Invalid time_of_report for {ticker} - {d}. Setting val to 'Invalid'\n")

            d = list(d)
            d[2] = 'Invalid'
            d = tuple(d)
        
        rel_dates = find_relative_dates(d[1], d[2] == "Before Open")
        rows.append(create_row(d, rel_dates))
            


    conn = db.get_conn()
    with conn.cursor() as curs:
        for r in rows: # each row is a tuple: (query, entry)
            try:
                print(f"Inserting row | {r[1]['ticker']} - {r[1]['report_date']}: ", traceback.format_exc())
                curs.execute(r[0], r[1])
            except:
                print(f"!!!!!!!!!!!!!!Failed to insert row for {ticker}!", traceback.format_exc())
                with open("./ph_errors.txt", "w", encoding="utf-8") as file:
                    file.write(f"\n\n[Insertion Failed!] {ticker} - {r[1]} :: {r[0]}\n")
        
    conn.commit()




def update_tickerlist(tickers):
    """
    After each ticker, update the tickerlist file with the remaining tickers. This makes it easier if there is a problem with the script,
    I can just re-run it and it will pickup where it left off
    """
    print(f"Updating tickerlist before starting next ticker. Writing {len(tickers)} tickers.")
    with open("./tickerlist.txt", "w", encoding="utf-8") as file:
        file.write("\n".join(tickers))

# get list of tickers that still need to be populated in db
with open("./tickerlist.txt", "r", encoding="utf-8") as file:
    tickers = [line.strip() for line in file]

# loop through tickers 1 at a time. 
print(f"Retrieving and inserting data for {len(tickers)} tickers. Starting with {tickers[-1]}")
#while len(tickers) > 0:
#    t = tickers.pop()
#    print(f"Next Ticker: {t}")
#    populate_prices(t)



populate_prices('hut')
#db.close_conn()