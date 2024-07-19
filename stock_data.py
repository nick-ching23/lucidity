import requests
import pandas as pd
from bs4 import BeautifulSoup
from alpha_vantage.fundamentaldata import FundamentalData
from alpha_vantage.timeseries import TimeSeries
from datetime import datetime, timedelta
from openai import OpenAI

class stock_data:

    def __init__(self, symbol, ALPHA_API_KEY, GPT_API_KEY):
        self.symbol = symbol
        self.API_KEY = ALPHA_API_KEY
        self.OPEN_AI_KEY = GPT_API_KEY

    def get_balance_sheet(self):

        # Fetching the balance sheet
        balance_sheet_url = f'https://www.alphavantage.co/query?function=BALANCE_SHEET&symbol={
            self.symbol}&apikey={self.API_KEY}'
        balance_sheet_response = requests.get(balance_sheet_url)
        balance_sheet_data = balance_sheet_response.json()
        balance_sheet_df = pd.DataFrame(balance_sheet_data['annualReports'])

        return balance_sheet_df

    def get_income_statement(self):
        # Fetching the income statement
        income_statement_url = f'https://www.alphavantage.co/query?function=INCOME_STATEMENT&symbol={
            self.symbol}&apikey={self.API_KEY}'
        income_statement_response = requests.get(income_statement_url)
        income_statement_data = income_statement_response.json()
        income_statement_df = pd.DataFrame(
            income_statement_data['annualReports'])

        return income_statement_df

    def get_cash_flow_statement(self):
        # Fetching the cash flow statement
        cash_flow_url = f'https://www.alphavantage.co/query?function=CASH_FLOW&symbol={
            self.symbol}&apikey={self.API_KEY}'
        cash_flow_response = requests.get(cash_flow_url)
        cash_flow_data = cash_flow_response.json()
        cash_flow_df = pd.DataFrame(cash_flow_data['annualReports'])

        return cash_flow_df

    def get_company_overview(self):

        # Get company overview for market cap and shares outstanding
        overview_url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={
            self.symbol}&apikey={self.API_KEY}"
        overview_data = requests.get(overview_url).json()

        return overview_data

    def get_all_statements(self):
        return self.get_balance_sheet(), self.get_income_statement(), self.get_cash_flow_statement(), self.get_company_overview()

   # METRICS FOR CALCULATING CAPM & WACC
    def get_risk_free_rate(self):

        # URL for the CNBC page with the 10-year Treasury yield
        url = "https://www.cnbc.com/quotes/US10Y"

        # Send a request to the URL and get the HTML content
        response = requests.get(url)
        html_content = response.content

        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(html_content, "html.parser")

        # Find the element containing the 10-year Treasury yield
        yield_element = soup.find("span", {"class": "QuoteStrip-lastPrice"})

        # Extract the yield value
        risk_free_rate = float(yield_element.text.strip("%")) / 100

        return risk_free_rate

    def get_market_risk_premium(self):
        # Get historical data for the S&P 500 index
        symbol = "SPY"
        function = "TIME_SERIES_WEEKLY_ADJUSTED"
        url = f"https://www.alphavantage.co/query?function={
            function}&symbol={symbol}&apikey={self.API_KEY}"
        response = requests.get(url)
        data = response.json()

        # get the risk free rate:
        risk_free_rate = self.get_risk_free_rate()

        # Convert the data to a DataFrame
        df = pd.DataFrame(data["Weekly Adjusted Time Series"]).T
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        df = df.astype(float)

        # Calculate weekly returns
        df["Weekly Return"] = df["5. adjusted close"].pct_change()

        # Calculate annual returns
        df["Year"] = df.index.year
        annual_returns = df.groupby("Year")["Weekly Return"].apply(
            lambda x: (1 + x).prod() - 1)

        average_annual_return = annual_returns.mean()
        print(f"Average Annual Return of S&P 500: {average_annual_return:.4f}")

        # Calculate market risk premium
        market_risk_premium = average_annual_return - risk_free_rate
        print(f"Market Risk Premium: {market_risk_premium:.4f}")

        return market_risk_premium, average_annual_return

    # AKA Cost of Equity
    def calculate_CAPM(self):

        risk_free_rate = self.get_risk_free_rate()
        market_risk_premium, average_annual_return = self.get_market_risk_premium()

        # Get company overview for market cap and shares outstanding
        overview_url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={
            self.symbol}&apikey={self.API_KEY}"
        overview_data = requests.get(overview_url).json()

        beta = float(overview_data["Beta"])
        capm = risk_free_rate + beta * market_risk_premium

        return capm, risk_free_rate, market_risk_premium, average_annual_return

   # DCF METHODS
    def forecast_fcf(self):
        """
        Given the financial statements:
        1. Calculate historical unlevered free cash flows (operating cash flow - capital expenditure)
        2. Calculate the Compound Annual Growth (5 year previous), to be used for forecasting growth 
        """

        # Calculating unlevered FCF
        self.cash_flow_df["freeCashFlow"] = self.cash_flow_df["operatingCashflow"].astype(
            float) - self.cash_flow_df["capitalExpenditures"].astype(float)

        # Extract the last 5 years of FCF
        fcf_values = self.cash_flow_df["freeCashFlow"].astype(
            float).head(5).values[::-1]

        # Calculate CAGR
        beginning_value = fcf_values[0]
        ending_value = fcf_values[-1]
        years = len(fcf_values) - 1
        cagr = (ending_value / beginning_value) ** (1 / years) - 1
        print(f"CAGR: {cagr:.4f}")

        forecast_years = 5
        fcf_forecasted = [ending_value *
                          (1 + cagr) ** i for i in range(1, forecast_years + 1)]
        print("Forecasted Free Cash Flows for the next 5 years:", fcf_forecasted)

        return fcf_forecasted, forecast_years, cagr

    def get_cost_of_debt(self, total_debt):
        """
        cost of debt is interest expense / total debt

        """

        # Calculate interest expense
        interest_expense = self.income_statement_df["interestExpense"].astype(
            float).iloc[0]

        # Estimate the cost of debt
        cost_of_debt = interest_expense / total_debt

        return cost_of_debt

    def get_wacc(self, income_statement_df, market_value_of_equity, total_debt, cost_of_equity, cost_of_debt):
        """
        calculating WACC requires the following: 
        Equity, Debt, tax rate, cost of equity, cost of debt

        We calculate the effective tax rate by: 
            effective tax rate = tax expense / pre tax income 

        We then just plug into WACC equation
        """

        # Get pre-tax income and tax expense
        pre_tax_income = float(
            income_statement_df["incomeBeforeTax"].astype(float).iloc[0])
        tax_expense = float(
            income_statement_df["incomeTaxExpense"].astype(float).iloc[0])

        # Calculate effective tax rate
        effective_tax_rate = tax_expense / pre_tax_income
        # print(f"Effective Tax Rate: {effective_tax_rate:.4f}")

        E = market_value_of_equity
        D = total_debt

        # Calculate WACC
        wacc = (E / (E + D)) * cost_of_equity + (D / (E + D)) * \
            cost_of_debt * (1 - effective_tax_rate)
        

        print(f"WACC: {wacc:.4f}")
        return wacc

    def discount_cash_flows(self, terminal_value, forecasted_fcf, wacc, forecast_years):

        pv_fcf = [fcf / (1 + wacc) ** year for year,
                  fcf in enumerate(forecasted_fcf, start=1)]

        # Discount the terminal value to present value
        pv_terminal_value = terminal_value / (1 + wacc) ** forecast_years

        # Calculate the enterprise value
        enterprise_value = sum(pv_fcf) + pv_terminal_value
        
        print("ENTERPRISE VALUE: " + str(enterprise_value))

        return enterprise_value

    def calculate_terminal_value(self, fcf_forecast):
        """
        Calculates the terminal value of the DCF:

        1. Perpetual growth rate set to 1.8%
        2. Calculate market value of equity 
        3. Calculate market value of debt
        4. Calculate the cost of equity (risk free rate + beta * market risk premium)
        5. Calculate the cost of debt 
        6. Calculate WACC 
        7. Calculate Terminal Value (fcf[-1] * (1 + g)/ (wacc - g)) [g = perpetual growth rate]
        """

        perpetual_growth_rate = 0.018
        market_value_of_equity = float(
            self.overview_data["MarketCapitalization"])
        total_debt = float(self.balance_sheet_df.iloc[0]['totalLiabilities'])
        cost_of_equity, risk_free_rate, market_risk_premium, average_annual_return = self.calculate_CAPM()
        cost_of_debt = self.get_cost_of_debt(total_debt)

        wacc = self.get_wacc(self.income_statement_df, market_value_of_equity,
                             total_debt, cost_of_equity, cost_of_debt)

        terminal_value = fcf_forecast[-1] * \
            (1 + perpetual_growth_rate) / (wacc - perpetual_growth_rate)

        print("TERMINAL VALUE: " + str(terminal_value))
        return terminal_value, wacc, risk_free_rate, market_risk_premium, average_annual_return

    def get_value_per_share(self, enterprise_value):
        """
        At this point, we only have enterprise value. But we would like to get equity value. 
        We accomplish this by adding cash and equivalents and subtracting debt. 

        returns value per share
        """

        # Get the most recent year's data
        latest_balance_sheet = self.balance_sheet_df.iloc[0]

        # Extract total debt and cash and equivalents
        total_debt = float(latest_balance_sheet["totalLiabilities"])
        cash_and_equivalents = float(
            latest_balance_sheet["cashAndCashEquivalentsAtCarryingValue"])
        shares_outstanding = float(self.overview_data["SharesOutstanding"])
        equity_value = enterprise_value + cash_and_equivalents - total_debt
        value_per_share = equity_value / shares_outstanding
        
        print()
        print(enterprise_value)
        print(shares_outstanding)
        print(equity_value)
        print()
        
        
        
        return value_per_share

    def execute_dcf(self):
        """
        executes the dcf 
        """
        
        self.balance_sheet_df, self.income_statement_df, self.cash_flow_df, self.overview_data = self.get_all_statements()
        forecasted_fcf, forecast_years, cagr = self.forecast_fcf()
        terminal_value, self.wacc, risk_free_rate, market_risk_premium, average_annual_return = self.calculate_terminal_value(
            forecasted_fcf)
        enterprise_value = self.discount_cash_flows(
            terminal_value, forecasted_fcf, self.wacc, forecast_years)
        value_per_share = self.get_value_per_share(enterprise_value)
                
        dcf_valuation_data = {
            "cagr": cagr,
            "forecasted_free_cash_flows": forecasted_fcf,
            "risk_free_rate": risk_free_rate,
            "average_annual_return_sp500": average_annual_return,
            "market_risk_premium": market_risk_premium,
            "wacc": self.wacc,
            "fair_value_estimate": value_per_share,
        }
    
        print("DCF_VALUE: " + str(value_per_share))
        return value_per_share, dcf_valuation_data

    # RESIDUAL EARNINGS MODEL METHODS

    def get_book_value(self):

        # Initialize the Alpha Vantage API
        fd = FundamentalData(key=self.API_KEY, output_format='pandas')

        # Retrieve the balance sheet data to get the book value
        self.balance_sheet, _ = fd.get_balance_sheet_annual(symbol=self.symbol)

        print(self.balance_sheet.columns.tolist())

        self.balance_sheet.reset_index(inplace=True)

        # Ensure proper indexing
        self.balance_sheet.index = pd.RangeIndex(len(self.balance_sheet.index))

        # Remove any leading or trailing whitespace from column names
        self.balance_sheet.columns = self.balance_sheet.columns.str.strip()

        # Assuming the correct column name is 'totalShareholderEquity'
        try:
            book_value = self.balance_sheet.loc[0, 'totalShareholderEquity']
            book_value = float(book_value)  # Ensure it's a float
        except KeyError:
            print(
                "The column 'totalShareholderEquity' does not exist. Please check the available columns.")
            print(self.balance_sheet.columns.tolist())
            raise

        print("Book value: " + str(book_value))
        return book_value

    def get_earnings(self):

        fd = FundamentalData(key=self.API_KEY, output_format='pandas')

        # Retrieve the income statement data to get the earnings
        income_statement, _ = fd.get_income_statement_annual(
            symbol=self.symbol)
        income_statement.reset_index(inplace=True)
        income_statement.columns = income_statement.columns.str.strip()
        earnings = float(income_statement.loc[0, 'netIncome'])

        return earnings, income_statement[['fiscalDateEnding', 'netIncome']]

    def get_dividends(self):

        fd = FundamentalData(key=self.API_KEY, output_format='pandas')

        # Retrieve the cash flow data to get the dividends
        cash_flow, _ = fd.get_cash_flow_annual(symbol=self.symbol)
        cash_flow.reset_index(inplace=True)
        cash_flow.columns = cash_flow.columns.str.strip()
        dividends = cash_flow.loc[0, 'dividendPayout']

        if dividends != "None":
            return float(dividends), cash_flow[['fiscalDateEnding', 'dividendPayout']]

        print("Dividend value is 'None'")
        return 0, cash_flow[['fiscalDateEnding', 'dividendPayout']]

    def get_shares_outstanding(self):

        try:
            shares_outstanding = self.balance_sheet.loc[0,
                                                        'commonStockSharesOutstanding']
            shares_outstanding = float(
                shares_outstanding)  # Ensure it's a float
        except KeyError:
            print(
                "The column 'commonStockSharesOutstanding' does not exist. Please check the available columns.")
            print(self.balance_sheet.columns.tolist())
            raise

        print(shares_outstanding)
        return shares_outstanding

    def calculate_cagr(self, beginning_value, ending_value, periods):
        return (ending_value / beginning_value) ** (1 / periods) - 1

    def get_earnings_cagr(self, historical_earnings):
        beginning_value = float(
            historical_earnings['netIncome'].iloc[-1])  # Earliest year
        ending_value = float(
            historical_earnings['netIncome'].iloc[0])      # Latest year
        periods = len(historical_earnings) - 1
        cagr_rate = self.calculate_cagr(beginning_value, ending_value, periods)

        return cagr_rate

    def calculate_dividend_payout_ratio(self, dividends_paid, net_income):
        return dividends_paid / net_income

    def get_dividend_payout_ratio(self, historical_earnings, historical_dividends):

        # Align the datasets by fiscal date ending
        historical_data = pd.merge(
            historical_earnings, historical_dividends, on='fiscalDateEnding')

        historical_data['dividendPayout'] = historical_data['dividendPayout'].replace(
            'None', 0).astype(float)
        historical_data['netIncome'] = historical_data['netIncome'].replace(
            'None', 0).astype(float)

        # Debugging: Print rows to see the data before applying the lambda function
        print(historical_data)

        # Calculate the average dividend payout ratio
        payout_ratios = historical_data.apply(
            lambda row: self.calculate_dividend_payout_ratio(
                float(row['dividendPayout']),
                float(row['netIncome'])
            ) if row['netIncome'] != 0 else 0, axis=1
        )
        return payout_ratios.mean()

    def get_earnings_start_value(self, historical_earnings):
        earnings_start_value = float(
            historical_earnings['netIncome'].iloc[-1])  # Earliest year
        return earnings_start_value

    def forecast_bv(self, book_value, earnings_start, earnings_cagr, dividend_payout_ratio):
        """
        This method will forecast future book values for a specific company. 
        """
        # Forecast future book values
        forecast_horizon = 5  # Number of years to forecast
        forecasted_book_values = [book_value]

        for i in range(forecast_horizon):
            # Project future earnings based on the growth rate
            projected_earnings = earnings_start * \
                ((1 + earnings_cagr) ** (i + 1))

            # Estimate future dividends based on the payout ratio
            projected_dividends = projected_earnings * dividend_payout_ratio

            # Calculate the new book value
            new_book_value = forecasted_book_values[-1] + \
                projected_earnings - projected_dividends
            forecasted_book_values.append(new_book_value)

        print("Forecasted Book Values: " + str(forecasted_book_values))

        return forecasted_book_values, forecast_horizon

    def calculate_residual_earnings(self, capm, forecast_horizon, earnings, forecasted_book_values):
        # Calculate residual earnings
        required_return = capm  # This will have to be CAPM, meaning we should probably make a separate folder to calculate CAPM since we'll probably use it a lot
        residual_earnings = []
        
        print("required return RE: " + str(capm))

        for i in range(forecast_horizon):
            re = earnings - (required_return * forecasted_book_values[i])
            residual_earnings.append(re)

        print("Residual Earning Values: " + str(residual_earnings))

        return residual_earnings

    def discount_residual_earnings(self, residual_earnings, forecast_horizon, required_return):
        # Discount residual earnings to present value
        discounted_residual_earnings = []

        for i in range(forecast_horizon):
            discounted_re = residual_earnings[i] / \
                ((1 + required_return) ** (i + 1))
            discounted_residual_earnings.append(discounted_re)

        print("Discounted Residual Earnings: " +
              str(discounted_residual_earnings))

        return discounted_residual_earnings

    def calculate_RE_continuing_value(self, residual_earnings, required_return, forecast_horizon, book_value, discounted_residual_earnings):

        growth_rate = 0.018

        # Calculate continuing value
        continuing_value = residual_earnings[-1] * \
            (1 + growth_rate) / (required_return - growth_rate)
        discounted_continuing_value = continuing_value / \
            ((1 + required_return) ** forecast_horizon)

        print("Continuing Value: " + str(continuing_value))
        print("Discounted continuing value: " +
              str(discounted_continuing_value))

        # Sum up the results
        intrinsic_value = book_value + \
            sum(discounted_residual_earnings or []) + \
            (discounted_continuing_value or 0)

        print("Intrinsic Value: " + str(intrinsic_value))

        return intrinsic_value, continuing_value, discounted_continuing_value

    def calculate_intrinsic_value_ps(self, intrinsic_value, shares_outstanding):
        # Calculate the intrinsic value per share
        intrinsic_value_per_share = intrinsic_value / shares_outstanding
        print("Intrinsic Value Per Share: " + str(intrinsic_value_per_share))

        return intrinsic_value_per_share

    def execute_residual_earnings_model(self):
        book_value = self.get_book_value()
        
        capm, risk_free_rate, market_risk_premium, average_annual_return = self.calculate_CAPM()
        
        earnings, historical_earnings = self.get_earnings()
        dividends, historical_dividends = self.get_dividends()
        shares_outstanding = self.get_shares_outstanding()

        earnings_cagr = self.get_earnings_cagr(historical_earnings)
        dividend_payout_ratio = self.get_dividend_payout_ratio(
            historical_earnings, historical_dividends)
        earnings_start = self.get_earnings_start_value(historical_earnings)

        forecasted_book_values, forecast_horizon = self.forecast_bv(
            book_value, earnings_start, earnings_cagr, dividend_payout_ratio)
        residual_earnings = self.calculate_residual_earnings(
            capm, forecast_horizon, earnings, forecasted_book_values)
        discounted_residual_earnings = self.discount_residual_earnings(
            residual_earnings, forecast_horizon, self.wacc)

        intrinsic_value, continuing_value, discounted_continuing_value = self.calculate_RE_continuing_value(
            residual_earnings, self.wacc, forecast_horizon, book_value, discounted_residual_earnings)
        
        intrinsic_value_per_share = self.calculate_intrinsic_value_ps(
            intrinsic_value, shares_outstanding)
        
        re_valuation_data = {
            "book_value": book_value,
            "forecasted_book_values": forecasted_book_values,
            "residual_earning_values": residual_earnings,
            "discounted_residual_earnings": discounted_residual_earnings,
            "continuing_value": continuing_value,
            "discounted_continuing_value": discounted_continuing_value,
            "intrinsic_value": intrinsic_value,
            "intrinsic_value_per_share": intrinsic_value_per_share
        }


        return intrinsic_value_per_share, re_valuation_data

    # RETRIEVES THE CURRENT SHARE PRICE, YEAR RANGE, DAY RANGE

    def get_current_shareprice_dayrange_yearrange(self):
        ts = TimeSeries(key=self.API_KEY, output_format='pandas')
        data, meta_data = ts.get_quote_endpoint(symbol=self.symbol)

        current_price = data['05. price']
        share_price = current_price['Global Quote']
        print(type(current_price))
        print(f"The current share price of AAPL is: {share_price}")

        day_range = float(data['03. high']) - float(data['04. low'])

        # # Year Range:
        # one_year_ago = datetime.today().date() - timedelta(days=365)
        # year_data = data.loc[one_year_ago:]
        # year_low = year_data['3. low'].min()
        # year_high = year_data['2. high'].max()
        # year_range = (year_low, year_high)

        return share_price, 0, day_range

    # determine if the stock is over or undervalued
    def evaluate_fair_value_estimate(self, current_shareprice, dcf_value, re_value):
        
        current_shareprice = float(current_shareprice)
        valuation_status = "Fair Value"
        average_valuation = current_shareprice    
        
    
        # assuming both valuation metrics are equal, we'll average them 
        
        if isinstance(re_value, str) and not isinstance(dcf_value, str): 
            average_valuation = dcf_value
        elif not isinstance(re_value, str) and isinstance(dcf_value, str):
            average_valuation = re_value
        elif not isinstance(re_value, str) and not isinstance(dcf_value, str):       
            average_valuation = (re_value + dcf_value)/2
        else: 
            average_valuation = current_shareprice
        
        print(average_valuation)
            
        lower_fair_value = current_shareprice - (0.1*current_shareprice)
        upper_fair_value = current_shareprice + (0.1*current_shareprice)


        if lower_fair_value <= average_valuation <= upper_fair_value:
            valuation_status = "Fair Value"
        elif average_valuation > current_shareprice: 
            valuation_status = "Undervalued"
        elif average_valuation < current_shareprice: 
            valuation_status = "Overvalued"
        
        print(valuation_status)
        
        return valuation_status
        
    # GENERATE CHATGPT RESPONSE:
    
    def get_re_gpt_prompt(self, re_value, re_valuation_data):
        
        if isinstance(re_value, str):
            return "The Residual Earnings Model is not appropriate for valuing this company."
        
        re_string = f"""
        
        I also implemented a different valuation method: the residual earnings model. You are are going to write a formal paragraph explaining what could be driving the different valuations. Speak specifically about general market conditions, trends and more. 
        
        RE Valuation:   
        Book value: {re_valuation_data['book_value']}
        Forecasted Book Values: {re_valuation_data['forecasted_book_values']}
        Residual Earning Values: {re_valuation_data['residual_earning_values']}
        Discounted Residual Earnings: {re_valuation_data['discounted_residual_earnings']}
        Continuing Value: {re_valuation_data['continuing_value']}
        Discounted Continuing Value: {re_valuation_data['discounted_continuing_value']}
        Intrinsic Value: {re_valuation_data['intrinsic_value']}
        Intrinsic Value Per Share: {re_valuation_data['intrinsic_value_per_share']}
        """
        
        return re_string
    
    def get_dcf_gpt_prompt(self, dcf_value, dcf_valuation_data):
        
        if isinstance(dcf_value, str):
            return "The DCF model is not appropriate for valuing this company."
        
        dcf_string = f"""
        
            DCF Valuation:
            CAGR: {dcf_valuation_data['cagr']}
            Forecasted Free Cash Flows for the next 5 years: {dcf_valuation_data['forecasted_free_cash_flows']}
            Risk-Free Rate (10-Year Treasury Yield): {dcf_valuation_data['risk_free_rate']}
            Average Annual Return of S&P 500: {dcf_valuation_data['average_annual_return_sp500']}
            Market Risk Premium: {dcf_valuation_data['market_risk_premium']}
            WACC: {dcf_valuation_data['wacc']}
            Fair Value Estimate: ${dcf_valuation_data['fair_value_estimate']} /share
            
            I have calculated that the resulting fair value estimate of this stock is: {dcf_valuation_data['fair_value_estimate']} /share.
            """
            
        return dcf_string

    def generate_gpt_response(self, symbol, current_shareprice, dcf_value, re_value, dcf_valuation_data, re_valuation_data):
        
        client = OpenAI(api_key=self.OPEN_AI_KEY)
        dcf_string = self.get_dcf_gpt_prompt(dcf_value, dcf_valuation_data)
        re_string = self.get_re_gpt_prompt(re_value, re_valuation_data)
        
        # DCF and RE data in string format
        info_string = f"""
        Suppose I give you the stock {symbol}. Included are the valuations from a DCF and RE valuation models. You are a professor in corporate valuations giving a professional overview of a stock's value to a retail investor.
        ENSURE THAT YOU ARE USING UP TO DATE MARKET INFORMATION AND GENERAL KNOWLEDGE ABOUT THE COMPANY. FORMAT IN A PARAGRAPH. EMPHASIZE COMPANY RELATED REASONS FOR THIS VALUATION.
        {dcf_string}
       
        {re_string}
       
        The current value of {symbol} is: ${current_shareprice}. Use the above information to justify the valuation of the firm. tell me if the firm is overvalued or undervalued. Look at the given financial information and tell me what is driving the valuation of the company. Use general information and understanding of the company. Keep the paragraph short, professional and accessible.
        """

        print(info_string)

        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a professor in corporate valuations giving a professional overview of a stock's value to a retail investor. Look at the given financial information and tell me what is driving the valuation of the company. Use general information and understanding of the company. Keep the paragraph short, professional and accessible."},
                {"role": "user", "content": info_string}
            ]
        )

        # print(completion.choices[0].message.content)

        return completion.choices[0].message.content
