from wakepy import keep
import eps_scraper as eps
import psycopg2
import psycopg2.extras
import traceback
from logger import Logger

log = Logger("eps_runner")
conn = None

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
    with open("../../db/dbpassword", "r", encoding="utf-8") as file:
        dbpassword = file.readline().strip()

    # create database connection
    try:
        conn = psycopg2.connect(f"dbname='earni' user='earni' host='localhost' password='{dbpassword}'")
        log.log("Connected to earni database", True)
    except Exception as e:
        log.error("Failed to connect to database", traceback.format_exc())
        raise e

    return conn

def close_conn():
    """
    This method closes the connection to the database.
    """

    global conn
    if conn is not None:
        conn.commit()
        conn.close()
        conn = None

def get_tickers_from_db():
    """
    This method retrieves a list of all the tickers in the database.

    Returns:
        list: A list of all the tickers in the database.
    """

    conn = get_conn()

    with conn.cursor() as curs:
        try:
            curs.execute("SELECT (ticker) FROM companies")
            tickers = curs.fetchall()
        except Exception as e:
            log.error("Failed to get tickers from database", traceback.format_exc())
            raise e

    log.log(f"Retrieved {len(tickers)} tickers from the database", True)

    # clean up tickers since DB returns tuples
    for i in range(len(tickers)):
        tickers[i] = tickers[i][0]

    return tickers

def get_tickers():
    """
    Returns a list of all tickers in the remaining_tickers.txt file.
    Use this if script needs to be ran in parts, so we can pick up where we left off.
    """
    
    tickers = []
    with open("./remaining_tickers.txt", "r", encoding="utf-8") as file:
        for line in file:
            tickers.append(line.strip())

    return tickers


def scrape_eps(tickers):
    """
    takes a list of tickers and uses the eps_scraper module to scrape EPS data for each one.
    
    Args: tickers (list): list of ticker symbols to scrape EPS data for

    Returns: list: list of dictionaries containing the EPS data for each ticker
    """

    log.log("Scraping EPS data for all tickers in database", True)
    while len(tickers) > 0:
        #before each ticker, save the list of tickers left to scrape in case of failure - so we can pick up where we left off
        with open("./remaining_tickers.txt", "w", encoding="utf-8") as file:
            for t in tickers:
                file.write(f"{t}\n")

        ticker = tickers.pop(0) # I feel like starting from the front for some reason
        log.log(f"Scraping eps data for ticker {ticker}. {len(tickers)} tickers left", True)
        try:
            data = eps.scrape_eps(ticker)
            log.log(f"Inserting eps data for ticker {ticker}. {len(data)} records", True)

            try:
                insert_eps(data)
            except Exception as e:
                # Write failed tickers to a file to make it quick and easy to debug or cleanup later
                with open("./failed_tickers.txt", "a", encoding="utf-8") as file:
                    file.write(f"{ticker}\n")

                log.error(f"Failed to insert EPS data for ticker {ticker} with {len(data)} records.", traceback.format_exc())
                print(f"Failed to insert EPS data for ticker {ticker} with {len(data)} records.", traceback.format_exc()) 

        except Exception as e:
            log.error(f"Failed to scrape EPS data for ticker {ticker}", traceback.format_exc())
            print(f"Failed to scrape EPS data for ticker {ticker}", traceback.format_exc())



def insert_eps(eps_data):
    """
    This method writes all EPS data to the database
    """

    # grab database password from file
    conn = get_conn()

    insert_query = """
    INSERT INTO earnings_reports (
        ticker,
        date,
        period_end,
        eps_reported,
        eps_estimate,
        surprise,
        surprice_percent,
        time_of_report
    )
    VALUES (
        %(ticker)s,
        %(date)s,
        %(period_end)s,
        %(eps_reported)s,
        %(eps_estimate)s,
        %(surprise)s,
        %(surprise_percent)s,
        %(time_of_report)s
    )
    """

    with conn.cursor() as curs:
        try:
            for record in eps_data:
                curs.execute(insert_query, record)

            conn.commit()
        except Exception as e:
            conn.rollback() # rollback the transaction so we don't have partial data for any tickers. Easier to cleanup later, log will show which tickers failed
            log.error("insert_eps - Failed to insert EPS data into database", traceback.format_exc())
            print("insert_eps - Failed to insert EPS data into database", traceback.format_exc())
            raise e

        log.log("insert_eps - Successfully inserted EPS data into database", True)

if __name__ == "__main__":
    with keep.presenting():
        log.log("Retrieving tickers from the database", True)
        tickers = get_tickers()

        log.log(f"Succesfully retrieved {len(tickers)} tickers from the database. Scraping eps data for all", True)
        scrape_eps(tickers)

        log.log(f"Retrieved EPS data for {len(eps_data)} companies. Attempting to insert into database", True)

        log.log("Done!")




