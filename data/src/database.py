"""
    This module contains helper functions for accessing the earni databse.
    It is not generalized for database access as many functions will be specific to data in the earni db.
    May abstract parts out later for a general db class.
"""

import psycopg2
import traceback

conn = None

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
    with open("../../db/dbpassword", "r", encoding="utf-8") as file:
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