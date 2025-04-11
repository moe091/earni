from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import decimal
from datetime import datetime, date
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

fin_map = {
    "cashandcashequivalents": "cashandcashequivalentsatcarryingvalue",
    "cogs": "costofgoodsandservicessold"
}



db = SQLAlchemy()

def init_app(app):
    """Initialize the database with the Flask app"""
    db.init_app(app)

def query_financials(ticker, metrics, start_date=None, end_date=None):
    cols = [m for m in metrics if m in fin_fields]
    cols = [fin_map[c] for c in cols if c in fin_map]

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

    result_proxy = db.session.execute(text(sql), params)
    
    # Get column names from the result
    column_names = result_proxy.keys()
    
    # Convert to a list of dictionaries with proper type conversion
    result = []
    for row in result_proxy:
        row_dict = {}
        for i, column in enumerate(column_names):
            value = row[i]
            # Convert special types to JSON-serializable formats
            if isinstance(value, (datetime, date)):
                row_dict[column] = value.isoformat()
            elif isinstance(value, decimal.Decimal):
                row_dict[column] = float(value)
            else:
                row_dict[column] = value
                
        result.append(row_dict)
    
    return result

    
    