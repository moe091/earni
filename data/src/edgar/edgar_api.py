from datetime import datetime
import requests
import logging
from bs4 import BeautifulSoup
import traceback
import re

headers = {
    'User-Agent': 'Your Name (your.email@example.com)'
}


# create logger that logs to console, as well as .log and .err files. 
logger = logging.getLogger('EDGAR')
logger.setLevel(logging.DEBUG)  

log_format = logging.Formatter('[%(name)s :: %(levelname)s] %(message)s')

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_format)
logger.addHandler(console_handler)

log_handler = logging.FileHandler('edgar.log')
log_handler.setLevel(logging.DEBUG)
log_handler.setFormatter(log_format)
logger.addHandler(log_handler)

error_handler = logging.FileHandler('edgar.err')
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(log_format)
logger.addHandler(error_handler)


"""
    EdgarInstance is an instance of the edgar API for a single stock.
    It can also optionally specify a start date and will ignore filings from before that date

    it's purpose is to make handling filings much cleaner and easier when dealing with thousands of different companies. It wraps up all the 
    edgar API calls and data handling into a clean stateful object for a specific company, allowing it to be used without any hint of the complexity
    of the underlying API and data structures.


    Usage:
        amd = ea.EdgarInstance('amd')
        amd.populateFields(reports) # reports is a dict where each key is the ending date of a quarterly report
            populateFields will, for each xdoc, cycle through all 'contexts' and save ones where 'enddate' matches a key in 'reports'
            then cycle through all us-gaap fields and, if it's contextRef matches a saved context, add that field to the appropriate dict in 'reports'
                before adding a new field in a 'reports' dict, check if it already exists and if it has a different value. If it does, pause and alert so I can investigate

"""

class EdgarInstance:
    def __init__(self, ticker, start_date='1900-01-01'):
        """ Create an edgar instance for a specific ticker, with an optional start_date
        
        Args:
            ticker (str): the stock ticker to get filings for
            start_date (str, optional): the date to start getting filings from in 'YYYY-MM-DD' format. Defaults to 1900-01-01, which basically means to get ALL filings"""
        
        self.cik = get_cik(ticker)
        logger.debug(f"Creating EdgarInstance for {ticker}-{self.cik} with start date {start_date}")
        self.filing_list = request_all_filings(self.cik, start_date)
        self.filings = get_filing_info(self.filing_list, "10-Q")

        self.archive_pages = []
        self.xdocs = []

        for f_info in self.filings:
            f_info['archive_page'] = request_archive(self.cik, f_info['access_num'])
            doc_url = find_doc_url(f_info['archive_page'])
            f_info['xdoc_url'] = doc_url,
            f_info['xdoc'] = request_doc(doc_url).text
            f_info['soup'] = BeautifulSoup(f_info['xdoc'], features="xml")


    # NOTE: report_dates needs to be in format 09/2024 - months less than 10 need the '0' appended in front!!!!
    # TODO :: Can I break this function down? It's too deeply nested and complicated, doing too many things
    def populate_reports(self, report_dates):
        reports = {}
        for d in report_dates:
            reports[d] = {}
            
        for f in self.filings: # for each filing/xdoc we've pulled down
            contexts = f['soup'].find_all('context') # grab all the contexts from it's soup
            
            for c in contexts: # and for each of those contexts
                ed = c.find(re.compile(r'enddate', re.IGNORECASE)) # find it's enddate tag if it has one
                sd = c.find(re.compile(r'startdate', re.IGNORECASE)) # find it's enddate tag if it has one
                if ed is None or sd is None: 
                    print(f"enddate-{ed} or startdate-{sd} is None! Exiting")
                    continue # if it doesn't have an enddate or startdate tag, continue to the next report
                
                ed = datetime.strptime(ed.text, "%Y-%m-%d").date()
                sd = datetime.strptime(sd.text, "%Y-%m-%d").date()
                days = (ed - sd).days # find out how many days this context is covering to determine if it's actually quarterly data

                if days > 105 or days < 75: 
                    print(f"days({days}) out of range! exiting.  sd={sd} | ed={ed}")
                    continue # if the date range is ~90 days then move on to the next context, this one isn't quarterly
                ed = ed.strftime("%m/%Y") # put the endDate into the correct format so we can compare it against the report_dates passed in

                if ed in reports: # and if that enddate is a key in 'reports'
                    print(f"Matched a report for endDate {ed}!")
                    if 'context' not in reports[ed]: # if report for this enddate doesn't exist yet, intialize it as a list
                        reports[ed]['context'] = []
                    reports[ed]['context'].append(c) # then append the context to the reports dict for the given enddate

        return reports
               




######################################################################

def get_cik(ticker):
    with open("./cikmap.txt", "r") as file:
        cikmap = file.readlines()
        cikmap = [line.strip("\n") for line in cikmap]

    for line in cikmap:
        if line.split(" ")[0] == ticker:
            return line.split(" ")[1]

    return None


def request_filings(cik):
    # add leading 0's to CIK to make it 10 digits long because the url requires that
    cik = (10 - len(cik)) * "0" + cik
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"

    logger.info("\nGetting filings from URL: " + url)

    resp = requests.get(url, headers=headers)
    return resp.json()['filings']


def request_filing(filename):
    url = "https://data.sec.gov/submissions/" + filename
    print("Requesting Filing: ", url)
    resp = requests.get(url, headers=headers)
    return resp.json()

def request_all_filings(cik, start_date="1900-01-01"):
    filings = request_filings(cik)
    files = [request_filing(f['name']) for f in filings['files'] if f['filingTo'] > start_date] # gets info from the 'files' section of each filing(as opposed to 'recent' section)
    files.append(filings['recent']) # append the 'recent' files - now we have all the filing info for the given cik

    return files

def get_filing_info(filings, filing_type):
    """ Given a filing(or list of filings), returns a list of all 'accessionNumber's used to access documents of 'filing_type'(will probably only use 10-Q and maybe 10-K) 
    
        Args:
            filing (str | list): A filing or list of filings
            filing_type (str): filing_type of docs we are scanning for. e.g. 10-Q for quarterlies, 10-K for yearly reports 

        Returns:
            a list of accession number strings, dashes removed
    """
    if type(filings) != list:
        filings = [filings]
        
    filing_type = filing_type.lower() # in case there are inconsistencies in the edgar api data

    infos = []
    for filing in filings:
        indexes = []
        for i, r in enumerate(filing['primaryDocDescription']):
            if r.lower() == filing_type:
                print(f"{r.lower()} found at index {i}")
                indexes.append(i)        
            
        for i in indexes:
            print(f"Index {i} is {filing_type}. accessionNumber {i} is {filing['accessionNumber'][i]}")
            info = {
                'access_num': filing['accessionNumber'][i].replace("-", ""),
                'filing_date': filing['filingDate'][i],
                'filing_type': filing['primaryDocDescription'][i],
                'report_date': filing['reportDate'][i]
            }
            infos.append(info)
            
    return infos

def request_archive(cik, access_num):
    """ This function requests the index page for a given accessionNumber for a given company(cik). It is usually an HTML page that needs to be parsed to find the relevant xml docs """
    url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{access_num}"
    logger.debug(f"Requesting forms from: {url}")

    resp = requests.get(url, headers=headers)
    return resp.text


def find_doc_url(page):
    """ Finds the url of the actual xbrl doc on a given page. (use request_archive to get the page)"""
    soup = BeautifulSoup(page, "html.parser")
    links = soup.find_all('a')
    hrefs = [el.attrs['href'] for el in links]
    xml = [url for url in hrefs if "_htm.xml" in url]

    if len(xml) == 0: #if there is no link ending in _htm.xml, then check for files that end with digits followed by .xml
        pattern = re.compile(r'.*\d\.xml$')
        xml = [url for url in hrefs if pattern.match(url)]
        
    # # TODO :: ERROR CHECKING / HANDLING! Here and in all the _request functions!
    # if len(xml) == 0:
    #     logger.error("Unable to find xml file with XBRL data for page!")
    
    url = xml[0]
    if "http://" not in url:
        url = "https://www.sec.gov" + url
        

    return url


def request_doc(url):
    """ This function is used to request xblrp docs from the sec archives. Technically it could be used to request any url though... """
    resp = requests.get(url, headers=headers)
    return resp