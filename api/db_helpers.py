"""
    This module contains helper functions for accessing the earni databse.
    It is not generalized for database access as many functions will be specific to data in the earni db.
    May abstract parts out later for a general db class.
"""

import psycopg2
import traceback
from pathlib import Path
import logging


 # TODO :: move all the logging stuff somewhere else once I create an actual main script
logger = logging.getLogger(__name__)
logging.basicConfig(filename='earni_api.log')
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)  
console_formatter = logging.Formatter('[%(name)s :: %(levelname)s] %(message)s')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# get the path to the file with my pw in it. will research how to keep passwords secure and change this functionality before deploying this code anywhere
# TODO :: look into how to keep db passwords hidden in deployed apps
_pwpath = (Path(__file__).resolve().parent / ".." / "db" / "dbpassword").resolve()

# mapping from int values to column names, so that code can just use integer values to compare prices for different days
_col_names = {
    -30: "_minus_30", 
    -20: "_minus_20", 
    -10: "_minus_10", 
    -5: "_minus_5", 
    -4: "_minus_4", 
    -3: "_minus_3", 
    -2: "_minus_2", 
    -1: "_minus_1", 
    1: "_plus_1", 
    2: "_plus_2", 
    3: "_plus_3", 
    4: "_plus_4", 
    5: "_plus_5", 
    10: "_plus_10", 
    20: "_plus_20", 
    30: "_plus_30"
}

# add some more useful constructed fields. e.g. er_close_diff = close_plus_1 - close_minus_1
# valid fields, used for limiting/building SELECT clause
_valid_fields = {
    "ticker": "ph.ticker",
    "report_date": "ph.report_date",
    "period_end": "er.period_end",
    "eps_reported": "er.eps_reported",
    "eps_estimate": "er.eps_estimate",
    "eps_diff": "(er.eps_reported - er.eps_estimate)",
    "surprise": "er.surprise",
    "surprise_percent": "er.surprise_percent",
    "time_of_report": "er.time_of_report"
}
for t in ["close", "open", "high", "low", "volume"]:
    for c in _col_names:
        _valid_fields[t + _col_names[c]] = "ph." + t + _col_names[c]

# used in select clauses for constructed fields. If name exists in _special_fields, add the 'as xxxx'
# these values are duplicated in _valid_fields because WHERE clauses use the normal _valid_field strings. This is an extra check for SELECT clauses
# if i wanted to I could add a quick loop to append keys from _special_fields to _valid_fields, to remove the risks of code duplication, but I prefer knowing if I missed something
_special_fields = {
    "eps_diff": "(er.eps_reported - er.eps_estimate) as eps_diff"
}

# helper function to get a field based on it's name, and throw an error(or not) if it doesn't exist. Not used for special fields
# TODO :: shorten some previously written functions by making them use this instead of doing the same check on their own. maybe add an is_special named arg and have it handle that, if there is any need for it
def _get_field(name, is_strict):
    if not name in _valid_fields:
        if is_strict:
            logger.error(f"Failed to add value({name}, {type(name)}) to SELECT! value does not exist in _valid_fields")
            raise ValueError(f"Invalid SELECT field: {name}. Valid fields are: {list(_valid_fields)}")
        else:
            return name
    else:
        return _valid_fields[name]


""" 
    This class will provide very easy-to-use functions for all types of queries required by the API.
    The goal is that any possible query required by the API can be created in a straightforward and readable way, all the complexity
    is offloaded to this class so the actual API code can be super clean and streamlined, since that will be the most complicated
    and difficult part of this project
"""

class DatabaseHelper:
    def __init__(self):
        self.conn = None

        # use a builder pattern. user can build up a query step-by-step. Example:
        # dbh.select(["ticker", "date", "close_plus_1", "close_plus_5"]).whereIncrease(-5, -1).whereIncrease(1, 5).whereGreater("volume_plus_1", 1000).whereGreater("eps", "estimated_eps")
        # dbh.execute()
        self.options = {
            "SELECT": [],
            "FROM": "price_history ph JOIN earnings_reports er ON ph.ticker = er.ticker AND ph.report_date = er.date", # default from. If I end up needing different tables/joins I'll subclass and create separate helpers for different types of queries
            "WHERE": []
        }

    def connect(self):
        """
        This method creates a connection to the database, or returns one if it already exists.

        Returns:
            psycopg2.connection: A connection to the database.
        """

        # TODO :: check if conn is closed
        if self.conn is not None and self.conn.closed == 0:
            print("[api.db_helpers :: connect] Already connected to db, returning existing connection.")
            return
        
        # grab database password from file
        with open(_pwpath, "r", encoding="utf-8") as file:
            dbpassword = file.readline().strip()

        # create database connection
        try:
            self.conn = psycopg2.connect(f"dbname='earni' user='earni' host='localhost' password='{dbpassword}'")
            print("[api.db_helpers :: connect] Connected to earni database", True)
        except Exception as e:
            print("[api.db_helpers :: connect] Failed to connect to database", traceback.format_exc())
            raise

    

    def disconnect(self):
        """ This method closes the connection to the database. """
        if self.conn is not None:
            self.conn.commit()
            self.conn.close()
            self.conn = None

    
    def execute_sql(self, query):
        self.connect()

        with self.conn.cursor() as curs:
            curs.execute(query)
            return curs.fetchall()



    # executes query based on current self.params
    def execute(self):
        """ This function actually executes a query and returns the output. The other helper functions in this module are for building queries, but
            they need to be passed to this function to actually be executed """
        
        # build SELECT clause
        # TODO :: Throw error(or just add * ?) if options.SELECT is empty
        query = "SELECT "
        for s in self.options["SELECT"][:-1]: 
            query = query + s + ", "
        query = query + self.options["SELECT"][-1]

        # insert FROM clause
        query = query + " FROM " + self.options["FROM"]

        # create WHERE clause
        # TODO :: Throw error if options.WHERE is empty
        query = query + " WHERE " + self.options["WHERE"][0]
        for w in self.options["WHERE"][1:]:
            query = query + " AND " + w

        self.resetQuery()

        # TODO :: Execute query instead of just returning
        return self.execute_sql(query)


    def resetQuery(self):
        self.options = {
            "SELECT": [],
            "FROM": "price_history ph JOIN earnings_reports er ON ph.ticker = er.ticker AND ph.report_date = er.date", # default from. If I end up needing different tables/joins I'll subclass and create separate helpers for different types of queries
            "WHERE": []
        }


    def select(self, cols):
        # TODO :: Add hidden global variable for "valid_fields". If cols contains any values that aren't valid, throw an error and/or log a warning
        
        def add_select(val):
            if val in _valid_fields:
                if val in _special_fields:
                    self.options["SELECT"].append(_special_fields[val])
                else:
                    self.options["SELECT"].append(_valid_fields[val])
            else: # log and throw an error if val is invalid. We don't want queries to complete if there is anything wrong - better to give no output than incorrect or unexpected data
                logger.error(f"Failed to add value({val}, {type(val)}) to SELECT! value does not exist in _valid_fields")
                raise ValueError(f"Invalid SELECT field: {val}. Valid fields are: {list(_valid_fields)}")

        if type(cols) is not list:
            add_select(cols)
        else:
            for c in cols:
                add_select(c)

        return self
    

    def custom_select(self, a, operator, b, name):
        a = _get_field(a, True)
        b = _get_field(b, False)
        self.options["SELECT"].append(f"{a} {operator} {b} as {name}")
    

    def where_price_diff(self, a, b, amount=None, percent=None, type_a='close', type_b='close'):
        """ adds a where clause to the query, where a is greater than b.

            a and b represent days relative to ER date. -1 is the day before ER. 1 is the day after. 
            by default, the close price is used for both, but type_a and type_b can be set to 'close', 'open', 'high', or 'low'
            
            if amount and percent are both none, just do a > b
            if amount isn't none, do a > (b + amount)
            if percent isn't none, do a >= (b * percent)
            
            
            Args:
                a (int): days relative from the ER date for first comparator(the greater value), from which to take the price. e.g. -1 is the day before ER, 30 is 30 days after ER
                b (int): days relative from the ER date for second comparator(the lesser value)
                amount (float) - default None: how MUCH greater a needs to be than b. Default is None, which means it just needs to be greater at all
                percent (float) - default None: how much greater a needs to be than a, as a percentage. Default is none. Percent will only be used if amount is None and percent is not None
                type_a (string) - default 'close': which price to take for comparator a. possible values are 'close', 'open', 'high', 'low'
                type_a (string) - default 'close': which price to take for comparator b. possible values are 'close', 'open', 'high', 'low' """
        
        # convert a and b to the appropriate column names
        if a in _col_names:
            col_a = type_a + _col_names[a] # TODO :: add a _price_types hidden dict with valid type values. Throw/log error if an invalid type is passed in
        else: # log and throw an error if val is invalid. We don't want queries to complete if there is anything wrong - better to give no output than incorrect or unexpected data
            logger.error("Invalid arg 'a' passed into where_price_diff. Expected int with a value of -30 to 30, corresponding to price_history column names. Got: %s (type: %s)", a, type(a))
            raise ValueError(f"Invalid arg a: {a}, {type(a)}. Expected one of: 1, 2, 3, 4, 5, 10, 20, 30 (or the negative of any of these values)")


        if b in _col_names:
            col_b = type_b + _col_names[b] # TODO :: add a _price_types hidden dict with valid type values. Throw/log error if an invalid type is passed in
        else: # log and throw an error if val is invalid. We don't want queries to complete if there is anything wrong - better to give no output than incorrect or unexpected data
            logger.error("Invalid arg 'b' passed into where_price_diff. Expected int with a value of -30 to 30, corresponding to price_history column names. Got: %s (type: %s)", b, type(b))
            raise ValueError(f"Invalid arg b: {b}, {type(b)}. Expected one of: 1, 2, 3, 4, 5, 10, 20, 30 (or the negative of any of these values)")

        #print(f"[DEBUG :: where_price_diff] comparing {col_a} and {col_b}")

        if amount is not None: # we are doing an amount comparison. a > (b + amount). amount takes precedence if an amount and percent arg are passed in for some reason
            # NOTE :: I AM HERE. create the where clause(without the word WHERE - that's part of the build func) for a > (b + amount) type queries. Then do the same for percent. Then do the same for basic a > b
            clause = f"ph.{col_a} > ph.{col_b} + amount"
            self.options["WHERE"].append(clause)
            return self 
        elif percent is not None: # percent comparison. a > (b * percent)
            clause = f"ph.{col_a} > ph.{col_b} * {percent}"
            self.options["WHERE"].append(clause)
        else: # regular comparison. a > b
            clause = f"ph.{col_a} > ph.{col_b}"

        return self
    

    def where_value_is(self, prop, relation, val, offset=None):
        """ Creates a where clause where any given prop(column name) is related to(<, >, =, <=, >=, !=) a given number OR another property.
            if 'val' arg exists in _valid_fields, it will be treated as a column name. If not, it will be treated as a numeric value or string
            
            Args:
                prop (str): The name of the property to be compared(possible values are defined in _valid_fields)
                relation (str): The type of comparison: <, >, =, <=, >=, or !=
                val (not None): The value that prop is being compared against. If it exists in _valid_feilds, it will compare against that field. Otherwise it will be treated as a raw value
                offset (int or float): an offset applied to the 2nd value(val). Can be negative
        """

        if not prop in _valid_fields:
            logger.error(f"Invalid prop({prop}) passed into where_value_is. Valid prop names: {_valid_fields}")
            raise ValueError(f"Invalid arg prop: {prop}. Expected one of: {_valid_fields}")
        
        if val in _valid_fields:
            val = _valid_fields[val]
        
        if offset:
            clause = f"{_valid_fields[prop]} {relation} {val} + {offset}"
        else:
            clause = f"{_valid_fields[prop]} {relation} {val}"

        self.options["WHERE"].append(clause)

        return self


    


'''


NOTES

walking through an example use-case to figure out the most effective design:
"For all earnings_reports where the +1_closing price was 90% or less of the -1_closing price, AND the +5_closing price was 
105% or more of the +1_closing price, return the EPS, EPS_Estimate, EPS_Diff, -1_diff(-1_closing - -2_closing, day-before-ER price minus the 2-days-before-ER price)"

^ This means we want the EPS info and the pre-earnings price movement for all ERs that caused a large dip followed by a decent sized rebound.
(extra: allow a user-defined inverse or comparator. In this case it'd be ERs that caused a large dip followed by no rebound. +1 is 90% or less, but +5 is ~102% or less of +1.
this will allow easy side-by-side comparison to see what the differences are between companies that bounce back, vs ones that don't.
BONUS: retrieve headlines/articles around the earnings report and sentiment analyze)



'''












