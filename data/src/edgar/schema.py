# Helper functions for metric extraction

def get_revenue_value(filing_data):
    """
    Intelligently determine the most appropriate revenue value.
    
    For financial institutions (banks, credit services, etc.):
    - Prefers RevenuesNetOfInterestExpense if non-zero
    - Falls back to other revenue measures
    
    For non-financial companies:
    - Prefers Revenues
    - Falls back to other revenue measures
    
    Args:
        filing_data (dict): The filing data containing the financial metrics
        
    Returns:
        str or float: The most appropriate revenue value, or None if not found
    """
    # All potential revenue fields in priority order
    revenue_fields = [
        "RevenuesNetOfInterestExpense",
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet"
    ]
    
    # Check if this is likely a financial institution
    financial_indicators = [
        "Deposits", "InterestIncome", "InterestExpense", "LoanLossProvision",
        "NetInterestIncome", "NoninterestIncome", "LoansReceivableNet"
    ]
    is_financial = any(indicator in filing_data for indicator in financial_indicators)
    
    # For non-financial companies, swap the priority
    if not is_financial:
        revenue_fields[0], revenue_fields[1] = revenue_fields[1], revenue_fields[0]
    
    # Look for the first non-zero value among revenue fields
    for field in revenue_fields:
        if field in filing_data:
            value = filing_data[field].get('value')
            # Check if value is non-zero
            try:
                if value and float(value) != 0:
                    return value
            except (ValueError, TypeError):
                # If value can't be converted to float, still use it
                if value:
                    return value
    
    # If we haven't returned yet, find any revenue field even if zero
    for field in revenue_fields:
        if field in filing_data:
            return filing_data[field].get('value')
    
    # No revenue fields found
    return None

financial_metrics = {
    # Revenue using a custom function for smart determination
    "Revenue": get_revenue_value,
    
    # Other metrics still using prioritized lists
    "Net Income": [
        "NetIncomeLoss",
        "ProfitLoss", 
        "NetEarningsLoss"
    ],
    
    "EPS Diluted": [
        "EarningsPerShareDiluted",  # Standard term
        "IncomeLossPerShareDiluted",  # Alternative but equivalent
        "EarningsLossPerShareDiluted"  # Less common variant
    ],
    
    "COGS": [
        "CostOfRevenue",  
        "CostOfGoodsAndServicesSold",
        "CostOfGoodsSold",
        "CostOfSales"
    ],
    
    "Total Assets": [
        "Assets",  # Most common term
        "TotalAssets",  # Explicitly indicates it's the total
        "ConsolidatedAssetsAmount"  # Used in consolidated financial statements
    ],
    
    "Total Liabilities": [
        "Liabilities",  # Most common term
        "TotalLiabilities",  # Explicitly indicates it's the total
        "ConsolidatedLiabilitiesAmount"  # Used in consolidated financial statements
    ],
    
    "Stockholders Equity": [
        "StockholdersEquity",  # Standard term
        "TotalEquity",  # Alternative that may include minority interests
        "TotalShareholdersEquity"  # Alternative phrasing
        # Removed: "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest" as it explicitly includes minority interests
    ],
    
    "Long Term Debt": [
        "LongTermDebt",  # Standard term for long-term debt only
        "LongTermBorrowings"  # Alternative term for long-term debt
        # Removed: "LongTermDebtAndCapitalLeaseObligations" - includes lease obligations which may not be debt
        # Removed: "DebtLongtermAndShorttermCombinedAmount" - includes short-term debt
    ],
    
    "Cash and Cash Equivalents": [
        "CashAndCashEquivalents",  # Standard term
        "CashAndCashEquivalentsAtCarryingValue"  # Same but specifies carrying value
        # Removed: "CashAndDueFromBanks" - banking-specific and might not include all cash equivalents
        # Removed: "CashCashEquivalentsAndShortTermInvestments" - includes short-term investments which are not cash equivalents
    ],
    
    "Goodwill": [
        "Goodwill",  # Clean, direct measure of goodwill
        "GoodwillGross"  # Before any impairments
        # Removed: "GoodwillAndIntangibleAssetsNet" - includes other intangible assets
    ],
    
    # Banking and Financial Specific Metrics
    "Deposits": [
        "Deposits",  # Most general term for total deposits
        "DepositLiabilities",  # Alternative term for total deposits
        "CustomerDeposits"  # Similar but focuses on customer origin
        # Removed: "DemandDepositAccounts" - specific deposit type, not total
        # Removed: "TimeDeposits" - specific deposit type, not total
    ],
    
    "Loans Held for Sale": [
        "LoansHeldForSale",  # Most direct term
        "LoansReceivableHeldForSaleAmount",  # More detailed but equivalent
        "FinancingReceivableHeldForSale"  # Alternative terminology
    ],
    
    "Net Loans": [
        "LoansReceivableNet",  # Most direct and common term
        "FinancingReceivableNet",  # Alternative terminology
        "FinancingReceivableExcludingAccruedInterestAfterAllowanceForCreditLoss"  # More specific version
        # Removed: "NetLoansFifth" - appears to be a specific category or segment
    ],
    
    "Loan Loss Reserves": [
        "AllowanceForCreditLosses",  # Modern terminology under CECL
        "LoanLossReserve",  # Classic terminology
        "AllowanceForDoubtfulAccountsReceivable",  # Alternative phrasing
        "AllowanceForLoanAndLeaseLosses"  # Includes lease losses but commonly used
    ],
    
    "CET1 Capital Ratio": [
        "CommonEquityTierOneCapitalRatio",  # Full official term
        "CET1CapitalRatio"  # Common abbreviation
        # Removed: "CoreCapitalRatio" - may refer to a different regulatory concept
        # Removed: "CapitalAdequacyRatio" - broader concept that includes other capital types
    ],
    
    "Non-Interest Income": [
        "NoninterestIncome",  # Standard banking term
        "NonInterestRevenue"  # Alternative phrasing
        # Removed: "FeeAndCommissionIncome" - component of non-interest income but not comprehensive
        # Removed: "OtherOperatingIncome" - may include items outside non-interest income
    ],
    
    # Operational Expenses
    "R&D Expense": [
        "ResearchAndDevelopmentExpense",  # Most specific and accurate
        "ResearchAndDevelopment"  # Slightly less specific but common
        # Removed: "TechnologyAndDevelopmentExpense" - may include broader tech costs beyond R&D
    ],
    
    "G&A Expense": [
        "GeneralAndAdministrativeExpense",  # Standard term
        "GeneralAndAdministrative"  # Alternate form without "Expense"
        # Removed: "OperatingAndAdministrativeExpense" - may include broader operating costs
    ],
    
    "Sales & Marketing Expense": [
        "SellingAndMarketingExpense",  # Most comprehensive
        "MarketingExpense",  # Component but major
        "SellingExpense"  # Component but major
        # Removed: "SellingGeneralAndAdministrativeExpense" - includes G&A, which we track separately
        # Removed: "AdvertisingExpense" - specific subset of marketing expenses
    ],
    
    # Cash Flow Metrics
    "Operating Cash Flow": [
        "NetCashProvidedByUsedInOperatingActivities",  # GAAP standard term
        "CashFlowsFromUsedInOperatingActivities",  # Alternative phrasing
        "OperatingCashFlow"  # Simplified term
    ],
    
    "Financing Cash Flow": [
        "NetCashProvidedByUsedInFinancingActivities",  # GAAP standard term
        "CashFlowsFromUsedInFinancingActivities",  # Alternative phrasing
        "FinancingCashFlow"  # Simplified term
    ],
    
    # Other Important Metrics
    "Deferred Revenue": [
        "ContractLiabilities",  # Modern ASC 606 terminology
        "DeferredRevenue",  # Traditional terminology
        "ContractWithCustomerLiability",  # Alternative ASC 606 phrasing
        "UnearntRevenue"  # Older terminology but still used
    ],
    
    "Capitalized Contract Costs": [
        "CapitalizedContractCostNet",  # Most comprehensive
        "DeferredContractCosts",  # Alternative terminology
        "ContractAcquisitionCosts"  # More specific but common component
    ],
    
    # Additional key metrics
    "Investing Cash Flow": [
        "NetCashProvidedByUsedInInvestingActivities",  # GAAP standard term
        "CashFlowsFromUsedInInvestingActivities",  # Alternative phrasing
        "InvestingCashFlow"  # Simplified term
    ],
    
    "Interest Expense": [
        "InterestExpense",  # Generic total
        "InterestExpenseDebt",  # Debt-specific but often the main component
        "InterestExpenseDebtExcludingAmortization"  # Clean interest expense
    ]
}