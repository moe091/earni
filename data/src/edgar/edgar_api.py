# TODO :: Rework XBRL parsing after researching financial metrics and XBRL formats. Instead of grabbing everything, I'll come up with a list of relevant fields and their us-gaap tag names
# and then determine exactly how to accurately pull them from the correct filing and date range/type while avoiding duplicates. 
from datetime import datetime
from collections import defaultdict
import requests
import logging
from bs4 import BeautifulSoup
import traceback
import re
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
sys.path.append(project_root)


gaap = re.compile(r'^us-gaap:', re.IGNORECASE)
headers = {
    'User-Agent': 'Your Name (your.email@example.com)'
}
mydir = os.path.dirname(os.path.abspath(__file__))

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

# TODO :: Ignore tags who's context has an 'explicitMember' element - these aren't the generalized values we want
# TODO :: check for negative/positive?
# TODO :: Work on list of relevant fields and their us-gaap tag names. Go through a handful of filings(10-k and 10-q) and create a list of ALL fields. Throwout useless ones, keep anything that might be meaningful 
"""
    GrossProfit (us-gaap:GrossProfit) - not all companies have this
    NetIncomeLoss (us-gaap:NetIncomeLoss)
    EarningsPerShareBasic (us-gaap:EarningsPerShareBasic)
    EarningsPerShareDiluted (us-gaap:EarningsPerShareDiluted)
    CashAndCashEquivalentsAtCarryingValue (us-gaap:CashAndCashEquivalentsAtCarryingValue)   
    RestrictedCashAndCashEquivalents (us-gaap:RestrictedCashAndCashEquivalents)
    OtherInvestments (us-gaap:OtherInvestments)
    LoansReceivableHeldForSaleAmount (us-gaap:LoansReceivableHeldForSaleAmount)
    Assets (us-gaap:Assets)
    Liabilities (us-gaap:Liabilities)
    StockholdersEquity (us-gaap:StockholdersEquity)
"""
class EdgarInstance:
    def __init__(self, ticker, start_date='1900-01-01'):
        """ Create an edgar instance for a specific ticker, with an optional start_date
        
        Args:
            ticker (str): the stock ticker to get filings for
            start_date (str, optional): the date to start getting filings from in 'YYYY-MM-DD' format. Defaults to 1900-01-01, which basically means to get ALL filings"""
        self.f_names = ['CashAndCashEquivalentsAtCarryingValue', 'RestrictedCashAndCashEquivalents', 'OtherInvestments', 'LoansReceivableHeldForSaleAmount']
        self.cik = get_cik(ticker)
        logger.debug(f"Creating EdgarInstance for {ticker}-{self.cik} with start date {start_date}")
        self.filing_list = request_all_filings(self.cik, start_date)
        
        quarterly_filings = get_filing_info(self.filing_list, "10-Q")
        annual_filings = get_filing_info(self.filing_list, "10-K")
        self.filings = quarterly_filings + annual_filings
        self.filings.sort(key=lambda x: x['filing_date'])

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
            
        temp = []

        for f in self.filings: # for each filing/xdoc we've pulled down
            soup = f['soup']
            refs = defaultdict(list) # dictionary for all relevant ID's in this filing. key will be the enddate, value will be list of ids(correspond to contextRef) 
            contexts = soup.find_all('context') # grab all the contexts from it's soup


            for c in contexts: # and for each of those contexts
                ed = c.find(re.compile(r'^enddate$', re.IGNORECASE)) # find it's enddate tag if it has one
                sd = c.find(re.compile(r'^startdate$', re.IGNORECASE)) # find it's enddate tag if it has one
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
                    reports[ed]['context'].append((c.attrs['id'], soup)) # then append the context to the reports dict for the given enddate(along with the rest of the soup)
                    
                    refs[ed].append(c.attrs['id']) # and add the contextRef to the refs dict for this enddate

            for ed, ids in refs.items():
                for id in ids: # for each contextRef in the ids list for the current enddate
                    for tag in soup.find_all(gaap, attrs={'contextRef': id}): # find all us-gaap tags
                        temp.append({'name': tag.name, 'value': tag, 'enddate': ed})


        return temp
    

    def get_quarter_data(self):
        """
        Extract us-gaap fields that have a corresponding context with an enddate matching the report date
        and a startdate that is approximately one quarter (75-105 days) before the enddate.
        Stores results in self.quarter_data organized by report_date.
        
        Returns:
            dict: The self.quarter_data dictionary
        """
        self.quarter_data = {}
        
        for filing in self.filings:
            # Format the report_date to MM/YYYY
            report_year, report_month, report_day = filing['report_date'].split("-")
            report_date = f"{report_month.zfill(2)}/{report_year}"
            
            logger.debug(f"Processing quarterly data for report date: {report_date}")
            
            # Initialize the entry for this report date if it doesn't exist
            if report_date not in self.quarter_data:
                self.quarter_data[report_date] = {}
            
            soup = filing['soup']
            contexts = soup.find_all('context')
            
            # Create a lookup for all contexts with matching enddate and quarterly duration
            context_map = {}
            for context in contexts:
                context_id = context.attrs.get('id')
                if not context_id:
                    continue
                    
                # Look for contexts with enddate and startdate tags
                ed_tag = context.find(re.compile(r'^enddate$', re.IGNORECASE))
                sd_tag = context.find(re.compile(r'^startdate$', re.IGNORECASE))
                
                if ed_tag is None or sd_tag is None:
                    continue
                    
                try:
                    # Parse the dates
                    ed_date = datetime.strptime(ed_tag.text, "%Y-%m-%d").date()
                    sd_date = datetime.strptime(sd_tag.text, "%Y-%m-%d").date()
                    
                    # Convert enddate to MM/YYYY format for comparison
                    ed_formatted = ed_date.strftime("%m/%Y")
                    
                    # Calculate duration in days
                    days = (ed_date - sd_date).days
                    
                    # Only keep contexts where enddate matches report date and duration is quarterly (75-105 days)
                    if ed_formatted == report_date and 75 <= days <= 105:
                        context_map[context_id] = context
                except ValueError:
                    logger.error(f"Error parsing dates in context {context_id}")
                    continue
            
            logger.debug(f"Found {len(context_map)} quarterly contexts for {report_date}")
            
            # Find all us-gaap elements with matching contexts
            gaap_elements = soup.find_all(gaap)
            
            for element in gaap_elements:
                # Extract the name without the namespace prefix
                name = element.name
                if ':' in name:
                    name = name.split(':', 1)[1]
                
                # Get the context reference
                context_id = element.attrs.get('contextRef')
                if not context_id or context_id not in context_map:
                    continue
                
                # Create an entry for this element
                element_entry = {
                    'value': element.text,
                    'tag': str(element),  # Full text of the us-gaap tag
                    'context': str(context_map[context_id])  # Full text of the context
                }
                
                # Add to the array of entries for this field name
                if name not in self.quarter_data[report_date]:
                    self.quarter_data[report_date][name] = []
                    
                self.quarter_data[report_date][name].append(element_entry)
        
        return self.quarter_data


    def getInstants(self):
        """
        Extract us-gaap fields that have a corresponding context with an 'instant' tag matching the report date.
        Stores results in self.instants organized by report_date.
        
        Each report date contains us-gaap entries where the field name is the key.
        Multiple entries for the same field name are stored in an array.
        
        Returns:
            dict: The self.instants dictionary
        """
        self.instants = {}
        
        for filing in self.filings:
            # Format the report_date to MM/YYYY
            report_year, report_month, report_day = filing['report_date'].split("-")
            report_date = f"{report_month.zfill(2)}/{report_year}"
            
            logger.debug(f"Processing instant fields for report date: {report_date}")
            
            # Initialize the entry for this report date if it doesn't exist
            if report_date not in self.instants:
                self.instants[report_date] = {}
            
            soup = filing['soup']
            contexts = soup.find_all('context')
            
            # Create a lookup for all contexts with matching instant date
            context_map = {}
            for context in contexts:
                context_id = context.attrs.get('id')
                if not context_id:
                    continue
                    
                # Look for contexts with an instant tag
                instant_tag = context.find(re.compile(r'^instant$', re.IGNORECASE))
                if instant_tag is None:
                    continue
                    
                try:
                    # Convert the instant date to MM/YYYY format
                    instant_date = datetime.strptime(instant_tag.text, "%Y-%m-%d").date()
                    instant_formatted = instant_date.strftime("%m/%Y")
                    
                    # Only keep contexts where instant date matches the report date
                    if instant_formatted == report_date:
                        context_map[context_id] = context
                except ValueError:
                    logger.error(f"Error parsing date in context {context_id}")
                    continue
            
            logger.debug(f"Found {len(context_map)} contexts with matching instant date for {report_date}")
            
            # Find all us-gaap elements with matching contexts
            gaap_elements = soup.find_all(gaap)
            
            for element in gaap_elements:
                # Extract the name without the namespace prefix
                name = element.name
                if ':' in name:
                    name = name.split(':', 1)[1]
                
                # Get the context reference
                context_id = element.attrs.get('contextRef')
                if not context_id or context_id not in context_map:
                    continue
                
                # Create an entry for this element
                element_entry = {
                    'value': element.text,
                    'tag': str(element),  # Full text of the us-gaap tag
                    'context': str(context_map[context_id])  # Full text of the context
                }
                
                # Add to the array of entries for this field name
                if name not in self.instants[report_date]:
                    self.instants[report_date][name] = []
                    
                self.instants[report_date][name].append(element_entry)
        
        return self.instants
    

    def parse_filing(self, filing):
        year, month, day = filing['report_date'].split("-")
        report_date = f"{month.zfill(2)}/{year}"

        print(f"Report Date: {report_date} - searching for matching contexts")
        soup = filing['soup']
        contexts = soup.find_all('context')

        ids = []
        for c in contexts:
            ed = c.find(re.compile(r'^enddate$', re.IGNORECASE))
            sd = c.find(re.compile(r'^startdate$', re.IGNORECASE))
            if ed is None or sd is None:
                continue
            ed = datetime.strptime(ed.text, "%Y-%m-%d").date()
            sd = datetime.strptime(sd.text, "%Y-%m-%d").date()    
            days = (ed - sd).days
            if days > 105 or days < 75:
                continue
            
            ed = ed.strftime("%m/%Y") 
            if ed == report_date:
                print(f"Found matching date({ed}) for report. Context ID: {c.attrs['id']}")
                ids.append(c.attrs['id'])

        return ids
    

    def parse_all_filings(self):
        """Parse all filings and store GAAP entries in self.gaaps organized by report date.
        
        Each report date contains us-gaap entries where each field name is a key.
        Multiple entries for the same field name are stored in an array.
        """
        self.gaaps = {}
        
        for filing in self.filings:
            report_year, report_month, report_day = filing['report_date'].split("-")
            report_date = f"{report_month.zfill(2)}/{report_year}"
            
            logger.debug(f"Parsing filing for report date: {report_date}")
            
            # Initialize the entry for this report date if it doesn't exist
            if report_date not in self.gaaps:
                self.gaaps[report_date] = {}
            
            soup = filing['soup']
            contexts = soup.find_all('context')
            
            # Create a lookup for all contexts by ID
            context_map = {}
            for context in contexts:
                context_id = context.attrs.get('id')
                if context_id:
                    context_map[context_id] = context
            
            logger.debug(f"Found {len(context_map)} contexts for {report_date}")
            
            # Find all us-gaap elements
            gaap_elements = soup.find_all(gaap)
            
            for element in gaap_elements:
                # Extract the name without the namespace prefix
                name = element.name
                if ':' in name:
                    name = name.split(':', 1)[1]
                
                # Get the context reference
                context_id = element.attrs.get('contextRef')
                if not context_id or context_id not in context_map:
                    continue
                
                # Create an entry for this element
                element_entry = {
                    'name': name,
                    'value': element.text,
                    'attrs': dict(element.attrs),
                    'context': context_map[context_id]
                }
                
                # Add to the array of entries for this field name
                if name not in self.gaaps[report_date]:
                    self.gaaps[report_date][name] = []
                    
                self.gaaps[report_date][name].append(element_entry)
        
        return self.gaaps

    def extract_data_from_filing(self, field_names, filing):
        """
        Extract specific us-gaap fields from a single filing.
        
        Args:
            field_names (list): A list of us-gaap field names to extract
            filing (dict): A single filing dictionary from self.filings
        
        Returns:
            tuple: (report_date, fields_dict) where report_date is the formatted date string
                and fields_dict is a dictionary of field names with their values, tags, and contexts.
        """
        # Format the report_date to MM/YYYY
        current_year, current_month, current_day = filing['report_date'].split("-")
        current_report_date = f"{current_month.zfill(2)}/{current_year}"
        
        logger.debug(f"Extracting data for report date: {current_report_date}")
        
        fields_dict = {}
        field_names_lower = [name.lower() for name in field_names]
        
        soup = filing['soup']
        contexts = soup.find_all('context')
        
        # Create maps for matching contexts
        matching_contexts = {}
        
        for context in contexts:
            context_id = context.attrs.get('id')
            if not context_id:
                continue
                
            # Check for enddate that matches report date
            ed = context.find(re.compile(r'^enddate$', re.IGNORECASE))
            if ed:
                try:
                    ed_date = datetime.strptime(ed.text, "%Y-%m-%d").date()
                    ed_formatted = ed_date.strftime("%m/%Y")
                    if ed_formatted == current_report_date:
                        matching_contexts[context_id] = context
                        continue
                except ValueError:
                    pass
                    
            # Check for instant that matches report date
            instant = context.find(re.compile(r'^instant$', re.IGNORECASE))
            if instant:
                try:
                    instant_date = datetime.strptime(instant.text, "%Y-%m-%d").date()
                    instant_formatted = instant_date.strftime("%m/%Y")
                    if instant_formatted == current_report_date:
                        matching_contexts[context_id] = context
                except ValueError:
                    pass
        
        logger.debug(f"Found {len(matching_contexts)} matching contexts for {current_report_date}")
        
        # Find all us-gaap elements that match our field names and have a matching context
        for element in soup.find_all(gaap):
            # Extract the name without the namespace prefix
            name = element.name
            if ':' in name:
                name = name.split(':', 1)[1]
                
            # Check if this is a field we're looking for
            if name.lower() not in field_names_lower:
                continue
                
            # Get the context reference
            context_id = element.attrs.get('contextRef')
            if not context_id or context_id not in matching_contexts:
                continue
                
            # Add this field to our results
            fields_dict[name] = {
                'value': element.text,
                'tag': str(element),
                'context': str(matching_contexts[context_id])
            }
        
        return current_report_date, fields_dict

    def extract_data(self, field_names):
        """
        Extract specific us-gaap fields from all filings and store in self.fields.
        
        Args:
            field_names (list): A list of us-gaap field names to extract
        
        Returns:
            dict: self.fields - A dictionary with report dates as keys. Each value is a dictionary 
                of field names with their values, tags, and contexts.
        """
        self.fields = {}
        
        for filing in self.filings:
            report_date, fields_dict = self.extract_data_from_filing(field_names, filing)
            
            if fields_dict:  # Only add if we found at least one field
                self.fields[report_date] = fields_dict
        
        return self.fields

    def get_field(self, field_name, report_date=None):
        """Get all GAAP entries matching the specified field name, ignoring case.
        
        Args:
            field_name (str): The GAAP field name to search for (case-insensitive)
            report_date (str, optional): If provided, only return entries from this report date
                                        in format 'MM/YYYY' (e.g., '09/2024')
            
        Returns:
            dict: A dictionary where each key is a report date and each value is an array
                of entries for the matched field name
        """
        if not hasattr(self, 'gaaps'):
            logger.warning("parse_all_filings() must be called before get_field()")
            return {}
        
        results = {}
        field_name_lower = field_name.lower()
        
        # Filter by report date if provided
        report_dates = [report_date] if report_date else self.gaaps.keys()
        
        for date in report_dates:
            if date not in self.gaaps:
                continue
                
            for name, entries in self.gaaps[date].items():
                if name.lower() == field_name_lower:
                    if date not in results:
                        results[date] = []
                    results[date].extend(entries)
        
        return results

    def list_fields(self, report_date=None):
        """Get an alphabetically ordered list of all GAAP field names.
        
        Args:
            report_date (str, optional): If provided, only return field names from this report date
                                        in format 'MM/YYYY' (e.g., '09/2024')
            
        Returns:
            list: A sorted list of all unique field names
        """
        if not hasattr(self, 'gaaps'):
            logger.warning("parse_all_filings() must be called before list_fields()")
            return []
        
        field_names = set()
        
        # Filter by report date if provided
        if report_date:
            if report_date in self.gaaps:
                field_names.update(self.gaaps[report_date].keys())
        else:
            # Get field names from all report dates
            for date_data in self.gaaps.values():
                field_names.update(date_data.keys())
        
        # Sort alphabetically and return as a list
        return sorted(list(field_names), key=str.lower)


######################################################################

def get_cik(ticker):
    with open(mydir + "/cikmap.txt", "r") as file:
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

def request_all_filings(cik, start_date="2900-01-01"):
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





def start():
    sofi = EdgarInstance('sofi')
    from api import db_helpers
    db = db_helpers.DatabaseHelper()

    def get_report_dates(ticker):
        db.select("period_end")
        db.where_ticker_is(ticker)
        res = db.execute()
        res = [re.sub(r'^(\d)/', r'0\1/', r[0]) for r in res]
        return res
    
    report_dates = get_report_dates('sofi')
    print(report_dates)
    temp = sofi.populate_reports(report_dates)
    return temp

if __name__ == "__main__":
    start()
    