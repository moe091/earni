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
fi
