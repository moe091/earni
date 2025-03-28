#!/bin/bash

# TODO :: setup pgpass file to avoid password prompts

DB_NAME="earni"
DB_USER="earni" 
USER_EXISTS=$(psql -U postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'") # if user already exists we can skip everything


if [ "USER_EXISTS" == "1" ]; then
    echo "USER $DB_USER already exists, skipping"
else
    echo "Creating user '$DB_USER'"
    psql -U postgres -c "CREATE USER $DB_USER WITH PASSWORD '$EARNI_DB_PW';" #EARNI_DB_PW is an environment variable
    psql -U postgres -c "CREATE DATABASE $DB_NAME WITH OWNER earni"
    
    psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE earni TO earni";
    # apparently the above line isn't enough to allow earni to modify tables as needed. TODO :: learn about db permissions more
    # leaving these lines here for future reference, this is what I had to do to get it working in my local env:
    # GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO earni;
    # ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO earni;
    # GRANT CREATE ON SCHEMA public TO earni;


    psql -U earni -c "CREATE TABLE companies (
        ticker VARCHAR(10) PRIMARY KEY,
        cik INT NOT NULL,
        name VARCHAR(100),
        sector VARCHAR(100),
        industry VARCHAR(100)
        )"

    psql -U earni -c "CREATE TABLE earnings_reports (
        report_id SERIAL PRIMARY KEY,
        ticker VARCHAR(10) NOT NULL,
        date DATE,
        period_end DATE,
        eps_reported NUMERIC,
        eps_estimate NUMERIC,
        surprise NUMERIC,
        surprice_percent NUMERIC,
        time_of_report VARCHAR(20),
        CONSTRAINT fk_ticker
            FOREIGN KEY (ticker)
                REFERENCES companies(ticker)
    );"

    psql -U earni -c "CREATE TABLE price_history (
        ticker VARCHAR(10) NOT NULL,
        report_date DATE NOT NULL,
        is_valid BOOLEAN DEFAULT true,
        
        open_minus_20 INTEGER,
        open_minus_30 INTEGER,
        open_minus_10 INTEGER,
        open_minus_5 INTEGER,
        open_minus_4 INTEGER,
        open_minus_3 INTEGER,
        open_minus_2 INTEGER,
        open_minus_1 INTEGER,
        open_plus_1 INTEGER,
        open_plus_2 INTEGER,
        open_plus_3 INTEGER,
        open_plus_4 INTEGER,
        open_plus_5 INTEGER,
        open_plus_10 INTEGER,
        open_plus_20 INTEGER,
        open_plus_30 INTEGER,
        
        close_minus_20 INTEGER,
        close_minus_30 INTEGER,
        close_minus_10 INTEGER,
        close_minus_5 INTEGER,
        close_minus_4 INTEGER,
        close_minus_3 INTEGER,
        close_minus_2 INTEGER,
        close_minus_1 INTEGER,
        close_plus_1 INTEGER,
        close_plus_2 INTEGER,
        close_plus_3 INTEGER,
        close_plus_4 INTEGER,
        close_plus_5 INTEGER,
        close_plus_10 INTEGER,
        close_plus_20 INTEGER,
        close_plus_30 INTEGER,

        high_minus_20 INTEGER,
        high_minus_30 INTEGER,
        high_minus_10 INTEGER,
        high_minus_5 INTEGER,
        high_minus_4 INTEGER,
        high_minus_3 INTEGER,
        high_minus_2 INTEGER,
        high_minus_1 INTEGER,
        high_plus_1 INTEGER,
        high_plus_2 INTEGER,
        high_plus_3 INTEGER,
        high_plus_4 INTEGER,
        high_plus_5 INTEGER,
        high_plus_10 INTEGER,
        high_plus_20 INTEGER,
        high_plus_30 INTEGER,

        low_minus_20 INTEGER,
        low_minus_30 INTEGER,
        low_minus_10 INTEGER,
        low_minus_5 INTEGER,
        low_minus_4 INTEGER,
        low_minus_3 INTEGER,
        low_minus_2 INTEGER,
        low_minus_1 INTEGER,
        low_plus_1 INTEGER,
        low_plus_2 INTEGER,
        low_plus_3 INTEGER,
        low_plus_4 INTEGER,
        low_plus_5 INTEGER,
        low_plus_10 INTEGER,
        low_plus_20 INTEGER,
        low_plus_30 INTEGER,

        volume_minus_20 INTEGER,
        volume_minus_30 INTEGER,
        volume_minus_10 INTEGER,
        volume_minus_5 INTEGER,
        volume_minus_4 INTEGER,
        volume_minus_3 INTEGER,
        volume_minus_2 INTEGER,
        volume_minus_1 INTEGER,
        volume_plus_1 INTEGER,
        volume_plus_2 INTEGER,
        volume_plus_3 INTEGER,
        volume_plus_4 INTEGER,
        volume_plus_5 INTEGER,
        volume_plus_10 INTEGER,
        volume_plus_20 INTEGER,
        volume_plus_30 INTEGER,
        
        PRIMARY KEY (ticker, report_date)
    );"


    psql -U earni -c "CREATE TABLE financials (
        ticker VARCHAR(10),
        fiscalDateEnding DATE,
        reportedCurrency VARCHAR(10),
        comprehensiveIncomeNetOfTax DECIMAL(20,2),
        costOfRevenue DECIMAL(20,2),
        costofGoodsAndServicesSold DECIMAL(20,2),
        depreciation DECIMAL(20,2),
        depreciationAndAmortization DECIMAL(20,2),
        ebit DECIMAL(20,2),
        ebitda DECIMAL(20,2),
        grossProfit DECIMAL(20,2),
        incomeBeforeTax DECIMAL(20,2),
        incomeTaxExpense DECIMAL(20,2),
        interestAndDebtExpense DECIMAL(20,2),
        interestExpense DECIMAL(20,2),
        interestIncome DECIMAL(20,2),
        investmentIncomeNet DECIMAL(20,2),
        netIncome DECIMAL(20,2),
        netIncomeFromContinuingOperations DECIMAL(20,2),
        netInterestIncome DECIMAL(20,2),
        nonInterestIncome DECIMAL(20,2),
        operatingExpenses DECIMAL(20,2),
        operatingIncome DECIMAL(20,2),
        otherNonOperatingIncome DECIMAL(20,2),
        researchAndDevelopment DECIMAL(20,2),
        sellingGeneralAndAdministrative DECIMAL(20,2),
        totalRevenue DECIMAL(20,2),
        accumulatedDepreciationAmortizationPPE DECIMAL(20,2),
        capitalLeaseObligations DECIMAL(20,2),
        cashAndCashEquivalentsAtCarryingValue DECIMAL(20,2),
        cashAndShortTermInvestments DECIMAL(20,2),
        commonStock DECIMAL(20,2),
        commonStockSharesOutstanding DECIMAL(20,2),
        currentAccountsPayable DECIMAL(20,2),
        currentDebt DECIMAL(20,2),
        currentLongTermDebt DECIMAL(20,2),
        currentNetReceivables DECIMAL(20,2),
        deferredRevenue DECIMAL(20,2),
        goodwill DECIMAL(20,2),
        intangibleAssets DECIMAL(20,2),
        intangibleAssetsExcludingGoodwill DECIMAL(20,2),
        inventory DECIMAL(20,2),
        investments DECIMAL(20,2),
        longTermDebt DECIMAL(20,2),
        longTermDebtNoncurrent DECIMAL(20,2),
        longTermInvestments DECIMAL(20,2),
        otherCurrentAssets DECIMAL(20,2),
        otherCurrentLiabilities DECIMAL(20,2),
        otherNonCurrentAssets DECIMAL(20,2),
        otherNonCurrentLiabilities DECIMAL(20,2),
        propertyPlantEquipment DECIMAL(20,2),
        retainedEarnings DECIMAL(20,2),
        shortLongTermDebtTotal DECIMAL(20,2),
        shortTermDebt DECIMAL(20,2),
        shortTermInvestments DECIMAL(20,2),
        totalAssets DECIMAL(20,2),
        totalCurrentAssets DECIMAL(20,2),
        totalCurrentLiabilities DECIMAL(20,2),
        totalLiabilities DECIMAL(20,2),
        totalNonCurrentAssets DECIMAL(20,2),
        totalNonCurrentLiabilities DECIMAL(20,2),
        totalShareholderEquity DECIMAL(20,2),
        treasuryStock DECIMAL(20,2),
        capitalExpenditures DECIMAL(20,2),
        cashflowFromFinancing DECIMAL(20,2),
        cashflowFromInvestment DECIMAL(20,2),
        changeInCashAndCashEquivalents DECIMAL(20,2),
        changeInExchangeRate DECIMAL(20,2),
        changeInInventory DECIMAL(20,2),
        changeInOperatingAssets DECIMAL(20,2),
        changeInOperatingLiabilities DECIMAL(20,2),
        changeInReceivables DECIMAL(20,2),
        depreciationDepletionAndAmortization DECIMAL(20,2),
        dividendPayout DECIMAL(20,2),
        dividendPayoutCommonStock DECIMAL(20,2),
        dividendPayoutPreferredStock DECIMAL(20,2),
        operatingCashflow DECIMAL(20,2),
        paymentsForOperatingActivities DECIMAL(20,2),
        paymentsForRepurchaseOfCommonStock DECIMAL(20,2),
        paymentsForRepurchaseOfEquity DECIMAL(20,2),
        paymentsForRepurchaseOfPreferredStock DECIMAL(20,2),
        proceedsFromIssuanceOfCommonStock DECIMAL(20,2),
        proceedsFromIssuanceOfLongTermDebtAndCapitalSecuritiesNet DECIMAL(20,2),
        proceedsFromIssuanceOfPreferredStock DECIMAL(20,2),
        proceedsFromOperatingActivities DECIMAL(20,2),
        proceedsFromRepaymentsOfShortTermDebt DECIMAL(20,2),
        proceedsFromRepurchaseOfEquity DECIMAL(20,2),
        proceedsFromSaleOfTreasuryStock DECIMAL(20,2),
        profitLoss DECIMAL(20,2),
        PRIMARY KEY (ticker, fiscalDateEnding)
    );"
fi
