import requests
import logging
import re
import os
import json
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from collections import defaultdict

# Configure logging
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

# Constants and configurations
HEADERS = {
    'User-Agent': 'Your Name (your.email@example.com)'
}

GAAP_PATTERN = re.compile(r'^us-gaap:', re.IGNORECASE)
QUARTERLY_MIN_DAYS = 75
QUARTERLY_MAX_DAYS = 105
ANNUAL_MIN_DAYS = 350
ANNUAL_MAX_DAYS = 380

class EdgarInstance:
    """
    EdgarInstance is a class that fetches and processes SEC filings for a specific stock ticker.
    It downloads 10-K and 10-Q forms, extracts us-gaap fields, and organizes the data by report date.
    """
    
    def __init__(self, ticker, start_date=None):
        """
        Initialize an EdgarInstance for a specific ticker.
        
        Args:
            ticker (str): The stock ticker symbol (e.g., 'msft', 'aapl')
            start_date (str, optional): The date to start retrieving filings from in 'YYYY-MM-DD' format.
                                      If None, defaults to 10 years ago.
        """
        self.ticker = ticker.lower()
        # If no start_date provided, default to 10 years ago
        if start_date is None:
            ten_years_ago = datetime.now() - timedelta(days=365 * 10)
            self.start_date = ten_years_ago.strftime('%Y-%m-%d')
        else:
            self.start_date = start_date
            
        logger.info(f"Creating EdgarInstance for {self.ticker} with start date {self.start_date}")
        
        # Get CIK number for the ticker
        self.cik = self._get_cik(self.ticker)
        if not self.cik:
            raise ValueError(f"Could not find CIK for ticker {self.ticker}")
        
        logger.info(f"Found CIK: {self.cik}")
        
        # Initialize data structures
        self.filings = {}
        self.raw_filings_data = []
        
        # Fetch and process filings
        self._fetch_filings()
        self._process_filings()
    
    def _get_cik(self, ticker):
        """
        Get the CIK (Central Index Key) for a given ticker.
        
        Args:
            ticker (str): The stock ticker symbol
            
        Returns:
            str: The CIK number, or None if not found
        """
        # First try from SEC's ticker-to-CIK API
        try:
            response = requests.get(
                "https://www.sec.gov/files/company_tickers.json", 
                headers=HEADERS
            )
            if response.status_code == 200:
                companies = response.json()
                for _, company in companies.items():
                    if company['ticker'].lower() == ticker.lower():
                        # Format CIK to 10 digits with leading zeros
                        return str(company['cik_str']).zfill(10)
        except Exception as e:
            logger.error(f"Error fetching CIK from SEC API: {e}")
        
        # Fallback to local file (if available)
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            with open(os.path.join(script_dir, "cikmap.txt"), "r") as file:
                for line in file:
                    parts = line.strip().split()
                    if parts[0].lower() == ticker.lower():
                        return parts[1].zfill(10)
        except Exception as e:
            logger.error(f"Error reading local CIK map: {e}")
        
        return None
    
    def _fetch_filings(self):
        """
        Fetch all the filings for the ticker from the SEC EDGAR API.
        Gets both 10-K (annual) and 10-Q (quarterly) filings.
        """
        url = f"https://data.sec.gov/submissions/CIK{self.cik}.json"
        logger.info(f"Fetching filings from: {url}")
        
        try:
            response = requests.get(url, headers=HEADERS)
            if response.status_code != 200:
                raise Exception(f"Failed to fetch filings: {response.status_code}")
            
            submissions = response.json()
            
            # Process both recent filings and older filings
            recent_filings = submissions['filings']['recent']
            
            # Check if there are more filings in the files section
            if 'files' in submissions['filings']:
                for file_info in submissions['filings']['files']:
                    if file_info['filingTo'] >= self.start_date:
                        file_url = f"https://data.sec.gov/submissions/{file_info['name']}"
                        logger.debug(f"Fetching additional filings from: {file_url}")
                        
                        file_response = requests.get(file_url, headers=HEADERS)
                        if file_response.status_code == 200:
                            additional_filings = file_response.json()
                            # Append only 10-K and 10-Q filings
                            self._filter_and_append_filings(additional_filings)
            
            # Add recent filings
            self._filter_and_append_filings(recent_filings)
            
            logger.info(f"Fetched {len(self.raw_filings_data)} 10-K and 10-Q filings")
            
        except Exception as e:
            logger.error(f"Error fetching filings: {e}")
            raise
    
    def _filter_and_append_filings(self, filings_data):
        """
        Filter filings to only include 10-K and 10-Q forms after the start date.
        
        Args:
            filings_data (dict): The raw filings data from SEC API
        """
        if not filings_data.get('accessionNumber'):
            return
            
        for i, form_type in enumerate(filings_data.get('form', [])):
            if form_type in ['10-K', '10-Q']:
                filing_date = filings_data.get('filingDate', [])[i]
                if filing_date >= self.start_date:
                    report_date = filings_data.get('reportDate', [])[i]
                    accession_number = filings_data.get('accessionNumber', [])[i].replace('-', '')
                    primary_doc = filings_data.get('primaryDocument', [])[i]
                    
                    self.raw_filings_data.append({
                        'access_num': accession_number,
                        'filing_date': filing_date,
                        'report_date': report_date,
                        'filing_type': form_type,
                        'primary_doc': primary_doc
                    })
    
    def _process_filings(self):
        """
        Process each filing by fetching the XBRL document and extracting us-gaap fields.
        """
        # Sort filings by report date (oldest first)
        self.raw_filings_data.sort(key=lambda x: x['report_date'])
        
        for filing_info in self.raw_filings_data:
            try:
                # Format report date to MM/YYYY
                year, month, day = filing_info['report_date'].split("-")
                report_date = f"{month.zfill(2)}/{year}"
                
                logger.info(f"Processing {filing_info['filing_type']} filing for {report_date}")
                
                # Fetch archive page
                archive_page = self._request_archive(filing_info['access_num'])
                filing_info['archive_page'] = archive_page

                # Find XBRL document URL
                xbrl_url = self._find_xbrl_doc_url(archive_page)
                filing_info['xbrl_url'] = xbrl_url
                if not xbrl_url:
                    logger.warning(f"No XBRL document found for {report_date}")
                    continue
                
                # Fetch XBRL document
                xbrl_response = requests.get(xbrl_url, headers=HEADERS)
                if xbrl_response.status_code != 200:
                    logger.warning(f"Failed to fetch XBRL document: {xbrl_response.status_code}")
                    continue
                
                # Parse XBRL document
                soup = BeautifulSoup(xbrl_response.text, features="xml")
                filing_info['xbrl_soup'] = soup
                # Extract and store relevant us-gaap fields
                self._extract_gaap_fields(soup, report_date, filing_info['filing_type'])
                
            except Exception as e:
                logger.error(f"Error processing filing {filing_info['access_num']}: {e}")
                continue
    
    def _request_archive(self, access_num):
        """
        Request the archive page for a given accession number.
        
        Args:
            access_num (str): The accession number for the filing
            
        Returns:
            str: The HTML content of the archive page
        """
        url = f"https://www.sec.gov/Archives/edgar/data/{self.cik}/{access_num}"
        logger.debug(f"Requesting archive page: {url}")
        
        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch archive page: {response.status_code}")
            
        return response.text
    
    def _find_xbrl_doc_url(self, page):
        """
        Find the URL of the XBRL document in the archive page.
        
        Args:
            page (str): The HTML content of the archive page
            
        Returns:
            str: The URL of the XBRL document, or None if not found
        """
        soup = BeautifulSoup(page, "html.parser")
        links = soup.find_all('a')
        
        # First look for _htm.xml files (more common in newer filings)
        for link in links:
            href = link.get('href', '')
            if '_htm.xml' in href:
                if not href.startswith('http'):
                    href = f"https://www.sec.gov{href}"
                return href
        
        # Then look for any .xml file that has a digit before the extension
        pattern = re.compile(r'.*\d\.xml$')
        for link in links:
            href = link.get('href', '')
            if pattern.match(href):
                if not href.startswith('http'):
                    href = f"https://www.sec.gov{href}"
                return href
        
        return None
    
    def _extract_gaap_fields(self, soup, report_date, filing_type):
        """
        Extract us-gaap fields from the XBRL document.
        
        Args:
            soup (BeautifulSoup): The parsed XBRL document
            report_date (str): The report date in MM/YYYY format
            filing_type (str): The filing type (10-K or 10-Q)
        """
        # Initialize entry for this report date if it doesn't exist
        if report_date not in self.filings:
            self.filings[report_date] = {'filing_type': filing_type}
        
        # Find all context elements
        contexts = soup.find_all('context')
        context_map = {}
        
        # Map context IDs to their elements
        for context in contexts:
            context_id = context.get('id')
            if context_id:
                context_map[context_id] = context
        
        # Filter contexts to those matching the report date
        matching_contexts = self._filter_contexts_by_report_date(context_map, report_date, filing_type)
        
        # Find all us-gaap elements
        gaap_elements = soup.find_all(GAAP_PATTERN)
        
        # Process each us-gaap element
        for element in gaap_elements:
            # Extract field name without namespace
            field_name = element.name
            if ':' in field_name:
                field_name = field_name.split(':', 1)[1]
            
            # Get context reference
            context_ref = element.get('contextRef')
            if not context_ref or context_ref not in matching_contexts:
                continue
            
            # Create field entry
            field_data = {
                'value': element.text,
                'tag': str(element),
                'context': str(matching_contexts[context_ref])
            }
            
            # Add field to filings dictionary
            if field_name not in self.filings[report_date]:
                self.filings[report_date][field_name] = field_data
    
    def _filter_contexts_by_report_date(self, context_map, report_date, filing_type):
        """
        Filter contexts to only include those matching the report date.
        For period data, filter by appropriate duration (quarterly or annual).
        
        Args:
            context_map (dict): A map of context IDs to context elements
            report_date (str): The report date in MM/YYYY format
            filing_type (str): The filing type (10-K or 10-Q)
            
        Returns:
            dict: A filtered map of context IDs to context elements
        """
        matching_contexts = {}
        
        for context_id, context in context_map.items():
            if context.find("xbrldi:explicitMember") is not None:
                continue

            # Check for instant contexts
            instant_tag = context.find('instant')
            if instant_tag:
                try:
                    instant_date = datetime.strptime(instant_tag.text, "%Y-%m-%d")
                    instant_formatted = instant_date.strftime("%m/%Y")
                    
                    if instant_formatted == report_date:
                        matching_contexts[context_id] = context
                except ValueError:
                    continue
            
            # Check for period contexts
            period_tag = context.find('period')
            if period_tag:
                start_date_tag = period_tag.find('startDate')
                end_date_tag = period_tag.find('endDate')
                
                if start_date_tag and end_date_tag:
                    try:
                        start_date = datetime.strptime(start_date_tag.text, "%Y-%m-%d")
                        end_date = datetime.strptime(end_date_tag.text, "%Y-%m-%d")
                        
                        # Calculate duration in days
                        days = (end_date - start_date).days
                        
                        # Format end date to MM/YYYY
                        end_formatted = end_date.strftime("%m/%Y")
                        
                        # Check if this is a matching context based on duration and end date
                        if end_formatted == report_date:
                            # For 10-Q, look for quarterly duration
                            if filing_type == '10-Q' and QUARTERLY_MIN_DAYS <= days <= QUARTERLY_MAX_DAYS:
                                matching_contexts[context_id] = context
                            # For 10-K, look for annual duration
                            elif filing_type == '10-K' and ANNUAL_MIN_DAYS <= days <= ANNUAL_MAX_DAYS:
                                matching_contexts[context_id] = context
                    except ValueError:
                        continue
        
        return matching_contexts
    
    def get_all_fields(self, report_date=None):
        """
        Get all us-gaap field names available in the filings.
        
        Args:
            report_date (str, optional): If provided, only return fields from this report date
                                       in format 'MM/YYYY' (e.g., '09/2024')
            
        Returns:
            list: A sorted list of all unique field names
        """
        field_names = set()
        
        if report_date:
            if report_date in self.filings:
                # Skip the 'filing_type' field which is not a us-gaap field
                field_names.update([key for key in self.filings[report_date].keys() if key != 'filing_type'])
        else:
            # Get field names from all report dates
            for date_data in self.filings.values():
                field_names.update([key for key in date_data.keys() if key != 'filing_type'])
        
        return sorted(list(field_names))
    
    def get_all_values(self, field_name):
        """
        Get all values for a specific field name across all report dates.
        
        Args:
            field_name (str): The us-gaap field name to retrieve
            
        Returns:
            dict: A dictionary where keys are report dates and values are the field data
        """
        result = {}
        
        for report_date, filing_data in self.filings.items():
            if field_name in filing_data:
                result[report_date] = filing_data[field_name]
        
        return result
    
    def get_report_dates(self):
        """
        Get all available report dates.
        
        Returns:
            list: A sorted list of all report dates in MM/YYYY format
        """
        return sorted(self.filings.keys())
    
    def get_filing_types(self):
        """
        Get the filing type for each report date.
        
        Returns:
            dict: A dictionary where keys are report dates and values are filing types
        """
        return {date: data.get('filing_type') for date, data in self.filings.items()}

    def populate_schema(self, schema):
        """
        Populates a financial schema with data from all filings.
        
        Args:
            schema (dict): A dictionary where keys are human-readable financial metric names
                          and values are either:
                          - lists of possible GAAP field names in priority order
                          - functions that take filing_data and return the appropriate value
                          
        Returns:
            dict: A dictionary where keys are report dates and values are dictionaries 
                 of schema keys mapped to their values in that filing
        """
        logger.info(f"Populating schema with {len(schema)} financial metrics")
        
        # Dictionary to store results for all report dates
        populated_values = {}
        
        # Process each report date
        for report_date, filing_data in self.filings.items():
            logger.debug(f"Processing report date: {report_date}")
            
            # Initialize a dictionary for this report date with None values for all schema keys
            populated_values[report_date] = {metric_name: None for metric_name in schema}
            
            # Add filing type to the output
            populated_values[report_date]['Filing Type'] = filing_data.get('filing_type')
            
            # Process each metric in the schema
            for metric_name, schema_value in schema.items():
                # Skip Filing Type which we already handled
                if metric_name == 'Filing Type':
                    continue
                    
                # Check if the schema value is a function
                if callable(schema_value):
                    try:
                        # Call the function with filing data
                        value = schema_value(filing_data)
                        populated_values[report_date][metric_name] = value
                        logger.debug(f"Used function to determine {metric_name} value: {value}")
                    except Exception as e:
                        logger.error(f"Error calling function for {metric_name}: {e}")
                        populated_values[report_date][metric_name] = None
                else:
                    # It's a list of field names - use the original logic
                    field_names = schema_value
                    
                    # Find all matching fields for this metric
                    matches = []
                    
                    for field_name in field_names:
                        if field_name in filing_data:
                            matches.append({
                                'field_name': field_name,
                                'value': filing_data[field_name]['value'],
                                'tag': filing_data[field_name]['tag'],
                                'context': filing_data[field_name]['context'],
                                'priority': field_names.index(field_name)  # Lower index = higher priority
                            })
                    
                    # If we found matches, process them
                    if matches:
                        # If we have multiple matches, log the details
                        if len(matches) > 1:
                            logger.info(f"Multiple matches found for {metric_name} in report date {report_date}:")
                            for match in matches:
                                logger.info(f"  Field: {match['field_name']}, Value: {match['value']}, Priority: {match['priority']}")
                        
                        # Sort matches by priority (lower index in the schema list = higher priority)
                        matches.sort(key=lambda x: x['priority'])
                        
                        # Take the highest priority match (first in the sorted list)
                        best_match = matches[0]
                        
                        # Add the value to the populated schema
                        populated_values[report_date][metric_name] = best_match['value']
                        
                        # Log the selection
                        if len(matches) > 1:
                            logger.info(f"Selected {best_match['field_name']} with value {best_match['value']} for {metric_name}")
        
        return populated_values

    def get_value_history(self, schema, metric_name):
        """
        Gets the historical values for a specific metric across all report dates.
        
        Args:
            schema (dict): The financial metrics schema
            metric_name (str): The human-readable metric name from the schema
            
        Returns:
            dict: A dictionary where keys are report dates and values are the metric values
        """
        # First, populate the schema if it hasn't been done
        populated_schema = self.populate_schema(schema)
        
        # Extract the specified metric across all report dates
        return {report_date: data.get(metric_name) 
                for report_date, data in populated_schema.items()}
    
    def analyze_metrics(self, schema, report_dates=None):
        """
        Analyzes metrics for trends across specified report dates.
        
        Args:
            schema (dict): The financial metrics schema
            report_dates (list, optional): List of report dates to analyze. If None, uses all dates.
            
        Returns:
            dict: A dictionary with metric analysis results
        """
        # Populate the schema
        populated_schema = self.populate_schema(schema)
        
        # Filter report dates if specified
        if report_dates:
            populated_schema = {date: data for date, data in populated_schema.items() 
                              if date in report_dates}
        
        # Sort the report dates
        sorted_dates = sorted(populated_schema.keys())
        
        # Dictionary to store analysis results
        analysis = {}
        
        # For each metric, calculate period-over-period changes
        for metric_name in schema.keys():
            metric_values = []
            metric_changes = []
            metric_change_pct = []
            
            # Collect values across report dates
            for date in sorted_dates:
                value = populated_schema[date].get(metric_name)
                
                # Try to convert to float if possible for calculations
                try:
                    if value is not None:
                        value = float(value)
                except (ValueError, TypeError):
                    pass
                    
                metric_values.append((date, value))
            
            # Calculate changes between periods
            for i in range(1, len(metric_values)):
                prev_date, prev_value = metric_values[i-1]
                curr_date, curr_value = metric_values[i]
                
                if prev_value is not None and curr_value is not None:
                    try:
                        # Only calculate if both values are numeric
                        if isinstance(prev_value, (int, float)) and isinstance(curr_value, (int, float)):
                            change = curr_value - prev_value
                            change_pct = ((curr_value / prev_value) - 1) * 100 if prev_value != 0 else None
                            
                            metric_changes.append((curr_date, change))
                            metric_change_pct.append((curr_date, change_pct))
                    except Exception as e:
                        logger.warning(f"Error calculating change for {metric_name}: {e}")
            
            # Store results in analysis dictionary
            analysis[metric_name] = {
                'values': metric_values,
                'changes': metric_changes,
                'change_percentages': metric_change_pct
            }
        
        return analysis


# Helper function to use the module directly
def get_edgar_data(ticker, start_date=None, field_name=None, schema=None):
    """
    Convenience function to quickly get data for a ticker.
    
    Args:
        ticker (str): The stock ticker symbol
        start_date (str, optional): The start date in YYYY-MM-DD format
        field_name (str, optional): A specific field to retrieve
        schema (dict, optional): A dictionary mapping human-readable metric names to GAAP field names
        
    Returns:
        dict: If field_name is provided, returns values for that field.
              If schema is provided, returns populated schema values.
              Otherwise, returns the EdgarInstance object.
    """
    instance = EdgarInstance(ticker, start_date)
    
    if schema:
        return instance.populate_schema(schema)
    elif field_name:
        return instance.get_all_values(field_name)
    else:
        return instance


# Example usage
if __name__ == "__main__":
    # Sample financial metrics schema
    financial_metrics = {
        "Revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "RevenuesNetOfInterestExpense"],
        "Net Income": ["NetIncomeLoss", "ProfitLoss"],
        "EPS Diluted": ["EarningsPerShareDiluted"],
        "Total Assets": ["Assets", "TotalAssets"],
        "Cash and Cash Equivalents": ["CashAndCashEquivalentsAtCarryingValue", "CashAndCashEquivalents"]
    }
    
    # Create an instance for Microsoft
    msft = EdgarInstance('msft')
    
    # Get all available report dates
    report_dates = msft.get_report_dates()
    print(f"Available report dates: {report_dates}")
    
    # Populate schema with values from all filings
    populated_schema = msft.populate_schema(financial_metrics)
    
    # Print the results for the most recent report date
    if report_dates:
        latest_report = report_dates[-1]
        print(f"\nFinancial metrics for {latest_report}:")
        for metric, value in populated_schema[latest_report].items():
            print(f"{metric}: {value}")
    
    # Compare key metrics across multiple periods
    if len(report_dates) >= 2:
        print("\nQuarter-over-quarter comparison:")
        metrics_analysis = msft.analyze_metrics(financial_metrics, report_dates[-2:])
        
        for metric, analysis in metrics_analysis.items():
            if analysis['change_percentages'] and analysis['change_percentages'][0][1] is not None:
                date, pct_change = analysis['change_percentages'][0]
                print(f"{metric}: {pct_change:.2f}% change in {date}")