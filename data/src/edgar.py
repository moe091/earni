"""
    This module is used to retrieve data from the SEC EDGAR database.
"""



def get_cik(ticker):
    """
        This method retrieves the CIK number for a given ticker. CIK numbers are used to identify stocks in requests to the EDGAR database.

        (NOTE: For now, the Ticker to CIK data is currently stored in a text file provided by the SEC. Eventually I'll probably migrate it to 
        a database for slighty faster access, and this function will need to be updated)

        Args: 
            ticker (str): The ticker symbol of the company.

        Returns:
            int: the CIK number of the company.
    """
    with open('./symbols.txt', 'r', encoding='utf-8') as file:
        cik = None
        for line in file:
            t, c = line.split('\t')

            print(f"Reading line: {t} - {c}")
            if t.strip() == ticker:
                cik = c
                print(f"FOUND TICKER: {t} - {c}")
                break

        print(f"Returning CIK: {cik}")
        return cik

            