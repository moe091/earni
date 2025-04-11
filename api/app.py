from flask import Flask, request
import util.db as db

app = Flask(__name__)


@app.route('/')
def index():
    return "Flask API index page"


@app.route('/v1')
def api():
    return "Flask API endpoint"

@app.route('/v1/financial-data')
def financial_data():
    ticker = request.args.get('ticker')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    metrics = request.args.getlist('metric')
    
    data = db.query_financials(ticker, metrics, start_date, end_date)
    return data

if __name__ == '__main__':
    app.run(debug=True)