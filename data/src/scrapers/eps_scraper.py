"""
Scrapes EPS data from zacks
"""

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
from logger import Logger
import time
import traceback

chrome_service = None
driver = None
log = Logger("eps_scraper")

def start_driver():
    """
    Starts the chrome driver for selenium
    """
    global chrome_service, driver 

    if driver is None:
        chrome_service = Service("util/chromedriver-linux64/chromedriver")
        driver = webdriver.Chrome(service=chrome_service)
        driver.set_page_load_timeout(5)  # Timeout after 5 seconds


def load_page(ticker, attempts=5, delay=1):
    """ 
    Loads zacks page for a specific ticker. Zacks has a lot of background stuff that causes the load to timeout
    or fail, waiting longer doesn't work but retrying almost always does
    
    Args:
        ticker (str): ticker symbol of the company
        attempts (int): number of attempts to load the page (default 5)
        delay (int): delay between attempts in seconds (default 1)
    """
    for i in range(attempts):
        try: # try to load the page. If it works, break out of loop
            driver.get(f"https://www.zacks.com/stock/research/{ticker}/earnings-calendar")
            log.cur = ticker
            log.log(f"-------------------  Loaded page for {ticker}  -------------------")
            break
        except: # if load fails, wait 1s before looping and trying again
            if i == attempts - 1:
                print(f"[eps_scraper] Unable to load page for {ticker} after {attempts} attempts!")
                raise
            else:
                time.sleep(delay)

def expand_table(ticker):
    """ Executes some javascript to set the row count of the earnings table to 100, which is the max. I don't think the data goes over 60 rows for any tickers anyway"""

    # change table to show 100 rows with javascript
    driver.execute_script("""
                      dropdown = document.getElementsByName("earnings_announcements_earnings_table_length")[0];
                      event = new Event("change");
                      dropdown.value = 100;
                      dropdown.dispatchEvent(event)""")

    # wait for extra rows to load. If it takes too long just continue, some tickers only have a few rows available
    try:
        WebDriverWait(driver, 1).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, "table#earnings_announcements_earnings_table tr")) > 20
        )
    except:
        print(f"Unable to load extra rows for {ticker}. Continuing with what we have.")
        log.error(f"Unable to load extra rows for {ticker}. Continuing with what we have.")


def get_soup():
    """ Just gets the soup for the earnings table """

    # soupify the earnings table
    table = driver.find_element(By.ID, "earnings_announcements_earnings_table")
    soup = BeautifulSoup(table.get_attribute("innerHTML"), "html.parser")

    # remove attributes (don't really need this anymore, was just for visibility. Leaving it anyway because overhead is negligible and it'll be nice if I need to debug)
    for tag in soup.find_all(True):
        tag.attrs = {}
    
    return soup

def parse_soup(soup, ticker):
    """ parses the earnings table soup into a list of dictionaries containing all the data."""

    # parse the soup
    quarterlies = []
    #headers = soup.find('thead').find_all('th') # substituting my own header names. Keeping this for reference incase website changes
    headers = ['date', 'period_end', 'eps_estimate', 'eps_reported', 'surprise', 'surprise_percent', 'time_of_report']

    rows = soup.find('tbody').find_all('tr')

    # loop through each row in the table. each row represents a quarterly earnings report
    for r in rows: 
        vals = r.find_all(['th','td'])
        entry = {} # dict to store the current earnings report
        for i in range(len(vals)):
            entry[headers[i]] = vals[i].text.strip()
        entry['ticker'] = ticker
        quarterlies.append(entry)

    return quarterlies


def clean_data(reports, ticker):
    """
        Cleans earnings report data in-place to get it ready before inserting into the database

        Args:
            reports (list): list of dictionaries containing earnings_reports data
    """

    faulty = []
    for i in range(len(reports)):
        report = reports[i]
        try:
            report['date'] = datetime.strptime(report['date'], "%m/%d/%y")
            report['eps_estimate'] = float(report['eps_estimate'].replace("$", ""))
            report['eps_reported'] = float(report['eps_reported'].replace("$", ""))
            report['surprise'] = float(report['surprise'].replace("$", "").replace("+", "").replace("-", "").replace("%", ""))
            report['surprise_percent'] = float(report['surprise_percent'].replace("$", "").replace("+", "").replace("-", "").replace("%", ""))
        except:
            faulty.append(i)

    faulty.reverse() # reverse the list so we can remove items from the list without messing up the indices
    if len(faulty) > 0:
        log.warn(f"Unable to clean data for {len(faulty)} out of {len(reports)} reports for ticker {ticker}. Deleting them(details below)")
        for index in faulty:
            log.debug(f"faulty report at index {index}: {reports[index]}")
            del reports[index]



def scrape_eps(ticker):
    """
    Pulls EPS data(Date, EPS, Expected EPS, Difference, Surprise %) from quarterly earnings reports for a given stock

    Args:
        ticker (str): ticker symbol of the company
    
    Returns:
        eps_data (list): list of dictionaries containing the EPS data for all available earnings reports on zacks
    """

    # start_driver will check if chrome is already running, and start it if not
    start_driver()

    # load the zachs page for the given ticker. If page completely fails to load, log it so I can investigate manually later
    try:
        load_page(ticker)
    except Exception as e:
        log.error(f"load_page | Failed to load page for {ticker}: https://www.zacks.com/stock/research/{ticker}/earnings-calendar", traceback.format_exc())
        return []

    # expand the table to show all rows
    expand_table(ticker)

    # get the soup from the table
    soup = get_soup()

    # pull all the relevant data from the soup
    reports = parse_soup(soup, ticker)

    # clean the data and remove faulty entries, get it database-ready
    clean_data(reports, ticker)

    # return the cleaned earnings reports data
    print(f"Scraped {len(reports)} earnings reports for {ticker}")
    return reports

    










