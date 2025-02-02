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
    psql -U earni -c "CREATE TABLE companies (
        ticker VARCHAR(10) PRIMARY KEY,
        cik INT NOT NULL,
        name VARCHAR(100),
        sector VARCHAR(100),
        industry VARCHAR(100)
        )"
fi
