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
        earnings_report_date DATE NOT NULL,
        
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
        
        PRIMARY KEY (ticker, earnings_report_date)
    );:

fi
