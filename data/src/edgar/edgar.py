""" Typical Usage :: In case I come back to this file after a break and forget what it's actually used for 

    - get a list of cik #s(used in the SEC's edgar API to identify a company, mapped by ticker) by calling get_ciks()
    - get filings from EDGAR API by calling get_filings(cik) and passing in the cik for the company I want filings for
    - this returns a huge JSON doc with a bunch of info about retrieving thousands of different docs for the company. I usually want 10-Q(quarterly earnings) or 10-K(yearly) filings
    - call get_access_numbers(filing, type), passing in the filing(returned from get_filings) and the type I'm looking for(10-Q or 10-K). This will return a list of 'accessionNumbers' that I can use to locate those documents
    - NEXT - f"https://www.sec.gov/Archives/edgar/data/2488/{clean_acc}" use this url to get the filing for the given accessionNumber

"""


import requests
import logging
from bs4 import BeautifulSoup
import traceback
import re

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

# necessary headers for EDGAR requests used in multiple functions
headers = {
    'User-Agent': 'Your Name (your.email@example.com)'
}

def get_ciks():
    with open("./cikmap.txt", "r") as file:
        ciks = file.readlines()
        ciks = [line.strip("\n") for line in ciks]

    return ciks


def write_ciks(ciks):
    with open("./cikmap.txt", "w") as file:
        for c in ciks:
            file.write(c + "\n")


def get_url(cik, num):
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{num}"


def request_filings(cik):
    # add leading 0's to CIK to make it 10 digits long because the url requires that
    cik = (10 - len(cik)) * "0" + cik
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"

    logger.info("\nGetting filings from URL: " + url)

    resp = requests.get(url, headers=headers)
    return resp.json()['filings']


def get_access_numbers(filing, type):
    """ Returns a list of all 'accessionNumber's used to access documents of 'type'(will probably only use 10-Q and maybe 10-K) 
    
        Args:
            filing: the actual filing, e.g. resp['recent']
            type (str): type of docs we are scanning for. e.g. 10-Q for quarterlies, 10-K for yearly reports 

        Returns:
            a list of accession number strings, dashes removed
    """

    type = type.lower() # in case there are inconsistencies in the edgar api data
    indexes = []
    access_nums = []
    for i, r in enumerate(filing['primaryDocDescription']):
        if r.lower() == type:
            indexes.append(i)

    for i in indexes:
        access_nums.append(filing['accessionNumber'][i].replace("-", ""))

    return access_nums


def request_archive(cik, access_num):
    """ This function requests the index page for a given accessionNumber for a given company(cik). It is usually an HTML page that needs to be parsed to find the relevant xml docs """
    url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{access_num}"
    logger.debug(f"Requesting forms from: {url}")

    resp = requests.get(url, headers=headers)
    return resp.text


def find_doc_url(page):
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

def request_doc_soup(url):
    resp = request_doc(url)
    return BeautifulSoup(resp.text, "lxml")

# filings = request_filings(cik)
# a_nums = get_access_numbers(filings['recent'], "10-Q")            // or "10-K"
# page = request_archive(cik, a_nums[-1])
#
# url = find_doc_url(page)
# data = request_doc(url)
#
# BELOW LINES HAVE BEEN REPLACED BY THE ABOVE 2 LINES:
# use soup or something to parse the returned html. Looking for a link to a file that ends with "_htm.xml"
#   soup = BeautifulSoup(page, 'html.parser')
#   links = soup.find_all('a')
#   hrefs = [el.attrs['href'] for el in links]
#   xml = [url for url in hrefs if "_htm.xml" in url]
#   url = xml[0]
#   if url starts with http://, the request it. If not, append "https://www.sec.gov" then request it
def get_recent_filings(cik, type):
    filings = request_filings(cik)
    anums = get_access_numbers(filings['recent'], type)

    # making this an inner function to neatly log different errors for each step when iterating over a list of anums
    def extract_data(anum):
        try:
            page = request_archive(cik, anum)
        except:
            logger.error(f"{cik} - Unable to request_archive for accessionNumber: {anum}")
            return None

        try:
            url = find_doc_url(page)
        except:
            logger.error(f"{cik} Unable to find xml URL for XBRL data with accessionNumber: {anum}")
            return None

        try: # TODO :: check response code and log errors / handle non-200 responses
            data = request_doc(url)
        except:
            logger.error(f"{cik} Unable to download doc(anum={anum}) from URL: {url}")
            return None
        
        return data


    datas = []
    for anum in anums:
        data = extract_data(anum)
        if data is not None:
            datas.append(data)

    return datas



def check_filings(filings):
    """Checks a filings object(returned by get_filings) and returns any 'files' objects that contain data from within the last 10 years"""
    f = []
    for file in filings['files']:
        if file['filingTo'][:4] > "2015":
            f.append(file['name'])

    return f


