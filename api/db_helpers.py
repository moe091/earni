"""
    This module contains helper functions for accessing the earni databse.
    It is not generalized for database access as many functions will be specific to data in the earni db.
    May abstract parts out later for a general db class.
"""

import psycopg2
import traceback
from pathlib import Path

# get the path to the file with my pw in it. will research how to keep passwords secure and change this functionality before deploying this code anywhere
# TODO :: look into how to keep db passwords hidden in deployed apps
_pwpath = (Path(__file__).resolve().parent / ".." / "db" / "dbpassword").resolve()

class DatabaseHelper:
    def __init__(self):
        self.conn = None

    def connect(self):
        """
        This method creates a connection to the database, or returns one if it already exists.

        Returns:
            psycopg2.connection: A connection to the database.
        """

        # TODO :: check if conn is closed
        if self.conn is not None and self.conn.closed == 0:
            print("[api.db_helpers :: connect] Already connected to db, returning existing connection.")
            return self.conn
        
        # grab database password from file
        with open(_pwpath, "r", encoding="utf-8") as file:
            dbpassword = file.readline().strip()

        # create database connection
        # TODO :: implement real logging
        try:
            self.conn = psycopg2.connect(f"dbname='earni' user='earni' host='localhost' password='{dbpassword}'")
            print("[api.db_helpers :: connect] Connected to earni database", True)
        except Exception as e:
            print("[api.db_helpers :: connect] Failed to connect to database", traceback.format_exc())
            raise
    

    def disconnect(self):
        """
        This method closes the connection to the database.
        """
        if self.conn is not None:
            self.conn.commit()
            self.conn.close()
            self.conn = None