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

    "Gross Profit": [
        "GrossProfit", 
        "GrossProfitLoss"
    ],

    #Operating Margin Percentage - decided to calculate this as Operating Income / Revenue instead of checking for field, as it is more consistent
    #Free Cash Flow - decided to calculate this as Operating Cash Flow - Capital Expenditures instead of checking for field, as it is more consistent

    "Share Repurchases": [
        "PaymentsForRepurchaseOfCommonStock",
        "PaymentsToRepurchaseCommonStock"
    ],

    "Capital Expenditures": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsForPropertyPlantAndEquipment",
        "PaymentsForAcquisitionOfPropertyPlantAndEquipment",
        "CapitalExpenditures"
    ],

    "Current Liabilities": [
        "LiabilitiesCurrent",
        "CurrentLiabilities"
    ],

    "Inventory": [
        "InventoryNet",
        "Inventory"
    ],

    "Accounts Receivable": [
        "AccountsReceivableNetCurrent",
        "AccountsReceivableNet",
        "TradeAccountsReceivableNetCurrent"
    ],

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

    "OperatingIncomeLoss": [
        "OperatingIncomeLoss",  # Standard term
        "OperatingProfitLoss",  # Alternative but equivalent
        "OperatingEarningsLoss"  # Less common variant
    ],
    
    "Total Assets": [
        "ConsolidatedAssetsAmount", # if this exists it is the most comprehensive
        "TotalAssets",  # Explicitly indicates it's the total
        "Assets"  # Most common term
    ],
    
    "Total Liabilities": [
        "ConsolidatedLiabilitiesAmount",  # Most comprehensive
        "TotalLiabilities",  # Explicitly indicates it's the total
        "Liabilities"  # Most common term
    ],
    
    "Stockholders Equity": [ 
        "TotalShareholdersEquity", 
        "StockholdersEquity",
        "TotalEquity"  
    ],
    
    "Long Term Debt": [
        "LongTermDebt",  # Standard term for long-term debt only
        "LongTermBorrowings"  # Alternative term for long-term debt
    ],
    
    "Cash and Cash Equivalents": [
        "CashAndCashEquivalents",  # Standard term
        "CashAndCashEquivalentsAtCarryingValue"  # Same but specifies carrying value
    ],
    
    "Goodwill": [
        "Goodwill",  # Clean, direct measure of goodwill
        "GoodwillGross"  # Before any impairments
    ],
    
    # Banking and Financial Specific Metrics
    "Deposits": [
        "Deposits",  # Most general term for total deposits
        "DepositLiabilities"  # Alternative term for total deposits
    ],
    
    "Loans Held for Sale": [
        "LoansHeldForSale",  # Most direct term
        "LoansReceivableHeldForSaleAmount",  # More detailed but equivalent
        "FinancingReceivableHeldForSale"  # Alternative terminology
    ],
    
    "Net Loans": [
        "LoansReceivableNet",  # Most direct and common term
        "FinancingReceivableNet",  # Alternative terminology
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
    ],
    
    "Non-Interest Income": [
        "NoninterestIncome",  # Standard banking term
        "NonInterestRevenue"  # Alternative phrasing
    ],
    
    # Operational Expenses
    "R&D Expense": [
        "ResearchAndDevelopmentExpense",  # Most specific and accurate
        "ResearchAndDevelopment"  # Slightly less specific but common
    ],
    
    "G&A Expense": [
        "GeneralAndAdministrativeExpense",  # Standard term
        "GeneralAndAdministrative"  # Alternate form without "Expense"
    ],
    
    "Sales & Marketing Expense": [
        "SellingAndMarketingExpense",  # Most comprehensive
        "MarketingExpense",  # Component but major
        "SellingExpense"  # Component but major
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