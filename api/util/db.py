from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
fin_fields = [
    "totalrevenue",
    "costofrevenue",
    "cogs",
    "grossprofit",
    "operatingexpense",
    "ebit",
    "ebitda",
    "depreciation",
    "interestincome",
    "interestexpense",
    "netincome",
    "cashandcashequivalents",
    "totalassets",
    "totalliabilities",
    "totalshareholderequity",
    "goodwill",
    "inventory",
    "capitalexpenditures",
    "operatingcashflow"
]



db = SQLAlchemy()

def init_app(app):
    """Initialize the database with the Flask app"""
    db.init_app(app)

def query_financials(ticker, metrics, start_date=None, end_date=None):
    cols = [m for m in metrics if m in fin_fields]
    cols.insert(0, "fiscaldateending")
    # check for 'stockprice' and handle it on it's own
    sql = f"SELECT {', '.join(cols)} FROM financials WHERE ticker = :ticker"
    params = {"ticker": ticker}

    if start_date is not None:
        sql += f" AND fiscaldateending >= :start_date"
        params["start_date"] = datetime(int(start_date), 1, 1)
    
    if end_date is not None:
        sql += f" AND fiscaldateending <= :end_date"
        params["end_date"] = datetime(int(end_date), 12, 31)
    
    sql += " ORDER BY fiscaldateending DESC"

    print("\n\nBASE SQL:", sql) 
    print("PARAMS:", params)

    return db.session.execute(sql, params).fetchall()

    
    