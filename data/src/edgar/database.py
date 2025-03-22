"""
    This module contains helper functions for accessing the earni databse.
    It is not generalized for database access as many functions will be specific to data in the earni db.
    May abstract parts out later for a general db class.
"""

import psycopg2
import traceback
from pathlib import Path
import logging
import os
from decimal import Decimal, InvalidOperation
from datetime import datetime

columns = [
    "Revenue",
    "Gross Profit",
    "Share Repurchases",
    "Capital Expenditures",
    "Current Liabilities",
    "Inventory",
    "Accounts Receivable",
    "Net Income",
    "EPS Diluted",
    "COGS",
    "OperatingIncomeLoss",
    "Total Assets",
    "Total Liabilities",
    "Stockholders Equity",
    "Long Term Debt",
    "Cash and Cash Equivalents",
    "Goodwill",
    "Deposits",
    "Loans Held for Sale",
    "Net Loans",
    "Loan Loss Reserves",
    "CET1 Capital Ratio",
    "Non-Interest Income",
    "R&D Expense",
    "G&A Expense",
    "Sales & Marketing Expense",
    "Operating Cash Flow",
    "Financing Cash Flow",
    "Deferred Revenue",
    "Capitalized Contract Costs",
    "Investing Cash Flow",
    "Interest Expense",
    "Filing Type",
    "report_date",
    "date"
]

current_dir = Path(__file__).resolve().parent
pwpath = (current_dir / ".."  / ".." / ".." / "db" / "dbpassword").resolve()

conn = None

# Set up logging
logger = logging.getLogger('EDGAR_DB')
logger.setLevel(logging.INFO)

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# File handler for logging
log_handler = logging.FileHandler('logs/edgar_db_operations.log')
log_format = logging.Formatter('[%(asctime)s :: %(name)s :: %(levelname)s] %(message)s')
log_handler.setFormatter(log_format)
logger.addHandler(log_handler)

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
    with open(pwpath, "r", encoding="utf-8") as file:
        dbpassword = file.readline().strip()

    # create database connection
    try:
        conn = psycopg2.connect(f"dbname='earni' user='earni' host='localhost' password='{dbpassword}'")
        print("Connected to earni database", True)
    except Exception as e:
        print("Failed to connect to database", traceback.format_exc())
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

def update_financial_data(ticker, report_date, original_report_date, financial_data):
    """
    Create or update a row in the earnings_reports table with financial data from EDGAR.
    
    Args:
        ticker (str): The stock ticker symbol
        report_date (str): The report date in format 'MM/YYYY' (e.g., '03/2024')
        financial_data (dict): Dictionary containing financial metrics
    
    Returns:
        bool: True if operation was successful, False otherwise
    """
        # Set up ticker-specific logging
    ticker_logger = logging.getLogger(f'EDGAR_DB_{ticker}')
    ticker_logger.setLevel(logging.INFO)
    
    # Clear existing handlers to avoid duplicates
    ticker_logger.handlers = []
    
    # Create logs directory for tickers
    os.makedirs('logs/tickers', exist_ok=True)
    
    # Add ticker-specific file handler
    handler = logging.FileHandler(f'logs/tickers/{ticker}_edgar_db_operations.log')
    handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s'))
    ticker_logger.addHandler(handler)


    conn = get_conn()
    cursor = conn.cursor()
    
    try:
        # remove leading 0s from month to match db format
        if report_date and "/" in report_date:
            month, year = report_date.split("/")
            # Remove leading zeros from month
            month = str(int(month))
            report_date = f"{month}/{year}"
        else:
            ticker_logger.error(f"Invalid report_date format: {report_date} for {ticker}")
            return False
        
        # Check if row already exists
        cursor.execute(
            "SELECT report_id FROM earnings_reports WHERE ticker = %s AND period_end = %s",
            (ticker, report_date)
        )
        existing_row = cursor.fetchone()

        if not existing_row and original_report_date:
            try:
                # Parse the original date
                original_date = datetime.strptime(original_report_date, "%Y-%m-%d")
                day = original_date.day
                
                # Adjust month based on day value
                if day <= 15:
                    # Go back one month
                    if original_date.month == 1:
                        adjusted_date = datetime(original_date.year - 1, 12, 1)
                    else:
                        adjusted_date = datetime(original_date.year, original_date.month - 1, 1)
                else:
                    # Go forward one month
                    if original_date.month == 12:
                        adjusted_date = datetime(original_date.year + 1, 1, 1)
                    else:
                        adjusted_date = datetime(original_date.year, original_date.month + 1, 1)
                
                # Format the adjusted date to MM/YYYY with no leading zeros
                adjusted_report_date = f"{adjusted_date.month}/{adjusted_date.year}"
                
                ticker_logger.info(f"Trying adjusted date: {adjusted_report_date} (original: {report_date})")
                
                # Check if a row exists with the adjusted report_date
                cursor.execute(
                    "SELECT report_id FROM earnings_reports WHERE ticker = %s AND period_end = %s",
                    (ticker, adjusted_report_date)
                )
                adjusted_existing_row = cursor.fetchone()
                
                if adjusted_existing_row:
                    existing_row = adjusted_existing_row
                    report_date = adjusted_report_date
                    ticker_logger.info(f"Found existing row with adjusted date: {report_date}")
            except (ValueError, TypeError) as e:
                ticker_logger.warning(f"Could not adjust date: {original_report_date}: {str(e)}")


        
        # Validate data types and count non-zero fields for logging and consistency
        validated_data = {}
        non_zero_count = 0
        zero_fields = []
        error_fields = []
        
        for field, value in financial_data.items():
            # Skip None values
            if value is None:
                continue
            
            # For numeric fields, validate and convert
            if field != "Filing Type" and field != "original_report_date" and field != "Report Date":
                try:
                    # Convert to Decimal for numeric validation
                    decimal_value = Decimal(str(value))
                    if field in columns:
                        validated_data[field] = decimal_value
                    
                    # Track non-zero fields
                    if decimal_value != 0:
                        non_zero_count += 1
                    else:
                        zero_fields.append(field)
                        
                except (ValueError, TypeError, InvalidOperation):
                    error_fields.append((field, value))
                    ticker_logger.error(f"Invalid numeric value for {field}: {value}")
            else:
                # For Filing Type (string field)
                if field == "Filing Type":
                    validated_data[field] = value
                
                if not existing_row:
                    validated_data['date'] = original_report_date
        
        # Log warnings for zero values
        if zero_fields:
            ticker_logger.warning(f"{ticker} ({report_date}): Found zero values for fields: {', '.join(zero_fields)}")
        
        # Log errors for invalid fields
        if error_fields:
            field_errors = ', '.join([f"{field}={value}" for field, value in error_fields])
            ticker_logger.error(f"{ticker} ({report_date}): Invalid data types: {field_errors}")
            
        # Prepare data for SQL statement
        placeholders = []
        values = []
        
        for field, value in validated_data.items():
            placeholders.append(f'"{field}" = %s')
            values.append(value)
            
        if existing_row:
            # Update existing row
            if placeholders:
                update_sql = f"""
                UPDATE earnings_reports 
                SET {', '.join(placeholders)}
                WHERE ticker = %s AND period_end = %s
                """
                cursor.execute(update_sql, values + [ticker, report_date])
                ticker_logger.info(f"{ticker} ({report_date}): Updated existing record with {non_zero_count} non-zero financial metrics")
        else:
            ticker_logger.warning(f"{ticker} ({report_date}): No existing record found({report_date}, {original_report_date}) - creating new one")
            # Create new row
            fields = ['ticker', 'period_end'] + [f'"{field}"' for field in validated_data.keys()]
            placeholders = ['%s', '%s'] + ['%s'] * len(validated_data)
            
            insert_sql = f"""
            INSERT INTO earnings_reports ({', '.join(fields)})
            VALUES ({', '.join(placeholders)})
            """
            cursor.execute(insert_sql, [ticker, report_date] + list(validated_data.values()))
            ticker_logger.info(f"{ticker} ({report_date}): Created new record with {non_zero_count} non-zero financial metrics")
        
        conn.commit()
        return True
        
    except Exception as e:
        conn.rollback()
        ticker_logger.error(f"Error updating financial data for {ticker} ({report_date}): {str(e)}")
        return False