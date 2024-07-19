# app.py
from flask import Flask, request, jsonify, render_template, session
from stock_data import stock_data
import requests
import pandas as pd
import numpy as np
from dotenv import load_dotenv
import os

# LOADING ENVIRONMENTAL VARIABLES

load_dotenv() 

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['API_KEY'] = os.getenv('API_KEY')
app.config['GPT_API_KEY'] = os.getenv('GPT_API_KEY')

API_KEY = app.config['API_KEY'] 
SECRET_KEY = app.config['SECRET_KEY']
GPT_KEY = app.config['GPT_API_KEY']

app.secret_key = SECRET_KEY 

@app.route('/')
def index():
    return render_template('index.html')

# RUNS VALUATIONS, FORMULATES GPT QUERY
@app.route('/search')
def search():
    symbol = request.args.get('query')
    if not symbol:
        return jsonify({'error': 'No query provided'}), 400

    # RETRIEVE COMPANY OVERVIEW DATA
    url = f'https://www.alphavantage.co/query?function=OVERVIEW&symbol={symbol}&apikey={API_KEY}'
    response = requests.get(url)
    data = response.json()

    # EXECUTE DCF VALUE
    stock_class = stock_data(symbol, API_KEY, GPT_KEY)
    dcf_value, dcf_valuation_data =  stock_class.execute_dcf()

    if dcf_value < 0 or np.isnan(dcf_value): 
        dcf_value = "The DCF model is not appropriate for valuing this company."
    
    # EXECUTE RESIDUAL EARNINGS VALUE
    re_value, re_valuation_data =  stock_class.execute_residual_earnings_model()

    if re_value < 0 or np.isnan(re_value): 
        re_value = "The Residual Earnings Model is not appropriate for valuing this company."
   
    
    # HANDLE VALUATION ASSESSMENT
    current_shareprice, year_range, day_range = stock_class.get_current_shareprice_dayrange_yearrange()
    valuation_status = stock_class.evaluate_fair_value_estimate(current_shareprice, dcf_value, re_value)
    


    # HANDLING COMPANY FINANCIAL DATA OVERVIEW
    current_shareprice = abbreviate_number(float(current_shareprice))
    year_range = abbreviate_number(float(year_range))
    day_range = abbreviate_number(float(day_range))
    market_cap = abbreviate_number(data['MarketCapitalization'])
        
    session['symbol'] = symbol  # Store the symbol in the session


    # FORMULATE CHATGPT PROMPT & EXECUTE
    gpt_response = stock_class.generate_gpt_response(symbol, current_shareprice, dcf_value, re_value, dcf_valuation_data, re_valuation_data)
    
    re_value = abbreviate_number(re_value)  
    dcf_value = abbreviate_number(dcf_value)
    
    return render_template('search.html', company=data, dcf_value=dcf_value, re_value=re_value, valuation_status=valuation_status,
                           current_shareprice=current_shareprice, market_cap=market_cap, day_range=day_range, year_range=1.0, 
                           gpt_response=gpt_response)

@app.route('/data')
def get_data():
    symbol = session.get('symbol', 'AAPL')  # Default to 'AAPL' if no symbol is in the session
    url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={API_KEY}'
    response = requests.get(url)
    data = response.json()
    
    if "Time Series (Daily)" in data:
        time_series = data['Time Series (Daily)']
        df = pd.DataFrame.from_dict(time_series, orient='index')
        df = df.astype(float)
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        df['close'] = df['4. close']
        df = df[['close']]
        result = df.reset_index().to_dict(orient='records')
        return jsonify(result)
    else:
        return jsonify({"error": "Failed to retrieve data"}), 500

@app.route('/fetch-news')
def fetch_news():
    symbol = session.get('symbol', 'AAPL')
    url = f'https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={symbol}&time_from=20220410T0130&sort=RELEVANCE&apikey={API_KEY}'

    try:
        response = requests.get(url)
        data = response.json()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def abbreviate_number(value):
    if value is None:
        return ""

    if isinstance(value, str):
        return value
    
    value = float(value)
    if value >= 1_000_000_000_000:
        return f"${value / 1_000_000_000_000:.2f}T"
    elif value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    elif value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    elif value >= 1_000:
        return f"${value / 1_000:.2f}K"
    else:
        return f"${value:.2f}"


if __name__ == '__main__':
    app.run(debug=True)
