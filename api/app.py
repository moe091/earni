from datetime import datetime
from flask import Flask, jsonify, request, Response
import util.db as db
import util.charts as chart
from config import Config
import base64

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

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
        print("Columns:", data.columns)
        img_buffer = chart.create_price_chart(data, ticker, metrics)
        img_str = base64.b64encode(img_buffer).decode('utf-8')
        
        return f'<img src="data:image/png;base64,{img_str}" />'



    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True) 