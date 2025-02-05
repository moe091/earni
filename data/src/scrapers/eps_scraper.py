"""
Scrapes EPS data from zacks
"""

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import time

chrome_service = None
driver = None

def start_driver():
    """
    Starts the chrome driver for selenium
    """
    global chrome_service, driver 

    if driver is None:
        print("[eps_scraper] Starting chrome driver")
        chrome_service = Service("util/chromedriver-linux64/chromedriver")
        driver = webdriver.Chrome(service=chrome_service)
        driver.set_page_load_timeout(5)  # Timeout after 5 seconds
    else:
        print("[eps_scraper] Chrome driver running")


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
            print(f"[eps_scraper] Loading page: https://www.zacks.com/stock/research/{ticker}/earnings-calendar - attempt {i}")
            driver.get(f"https://www.zacks.com/stock/research/{ticker}/earnings-calendar")
            break
        except: # if load fails, wait 1s before looping and trying again
            if i == attempts - 1:
                print(f"[eps_scraper] Unable to load page for {ticker} after {attempts} attempts!")
                raise
            else:
                time.sleep(delay)


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

    # load the zachs page for the given ticker.
    load_page(ticker)

    print(f"[eps_scraper] Changing rows dropdown to 100")
    # change table to show 100 rows with javascript
    driver.execute_script("""
                      dropdown = document.getElementsByName("earnings_announcements_earnings_table_length")[0];
                      event = new Event("change");
                      dropdown.value = 100;
                      dropdown.dispatchEvent(event)""")

    print(f"[eps_scraper] Waiting for table to load")
    # wait for extra rows to load. If it takes too long just continue, some tickers only have a few rows available
    try:
        print("[DEBUG] Before - WebDriverWait")
        WebDriverWait(driver, 1).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, "table#earnings_announcements_earnings_table tr")) > 20
        )
        print("[DEBUG] After - WebDriverWait")
    except:
        print("Unable to load extra rows for {ticker}. Continuing with what we have.")

    print(f"[eps_scraper] pulling HTML from table")
    # soupify the earnings table
    table = driver.find_element(By.ID, "earnings_announcements_earnings_table")
    soup = BeautifulSoup(table.get_attribute("innerHTML"), "html.parser")

    # remove attributes (don't really need this anymore, was just for visibility. Leaving it anyway because overhead is negligible and it'll be nice if I need to debug)
    for tag in soup.find_all(True):
        tag.attrs = {}

    print(f"[eps_scraper] Parsing table")
    # parse the soup
    quarterlies = []
    headers = soup.find('thead').find_all('th')

    for i in range(len(headers)):
        headers[i] = headers[i].text.strip()

    rows = soup.find('tbody').find_all('tr')

    # loop through each row in the table. each row represents a quarterly earnings report
    for r in rows: 
        vals = r.find_all(['th','td'])
        entry = {} # dict to store the current earnings report
        for i in range(len(vals)):
            entry[headers[i]] = vals[i].text.strip()
        entry['ticker'] = ticker
        quarterlies.append(entry)

    for v in quarterlies:
        print(v)

    print("[eps_scraper] Done!")
    return quarterlies










