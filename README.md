# Lucidity: AI-Driven Stock Valuation Platform
Empowering financial decision-making through AI-driven insights into stock valuations.

## Overview
Lucidity is a cutting-edge financial platform that automates stock valuations using Discounted Cash Flow (DCF) and Real Estate (RE) models. By leveraging real-time financial data and advanced AI capabilities, Lucidity simplifies the process of financial statement modeling, allowing users to access and understand stock valuations with minimal manual effort. Integrated with Alpha Vantage API and powered by web scraping tools, Lucidity provides detailed financial data analysis while incorporating AI-driven explanations to justify and clarify valuation outcomes.

## Features
- **Automated DCF and RE Models**: Implements the DCF and RE models to evaluate stocks based on real-time data.
- **AI-Powered Valuation Explanations**: Uses ChatGPT-4o to explain discrepancies and provide insights into different valuation methodologies.
- **Real-Time Financial Data**: Pulls stock data via the Alpha Vantage API and scrapes treasury financial data from CNBC Finance.
- **User-Friendly Interface**: A Python-based backend and dynamic HTML/CSS/JavaScript frontend ensure ease of interaction for users looking to analyze stock valuations.
  
## Achievements
- **Automated Financial Modeling**: Provides full automation of the stock valuation process, aside from result interpretation, significantly streamlining the workflow for financial analysis.
- **AI Integration**: Innovatively uses AI to explain complex financial concepts, making valuation results accessible to non-experts.

## Demo
[Technical Demo](#)

## Installation
To set up Lucidity for development or personal use, follow these steps:

1. **Clone the Git Repository**:
    ```bash
    git clone https://github.com/nick-ching23/lucidity.git
    cd lucidity
    ```

2. **Set Up a Virtual Environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Unix/macOS
    .\venv\Scripts\activate   # On Windows
    ```

3. **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4. **Run the Application**:
    ```bash
    python3 main.py
    ```

## Usage
After launching Lucidity, navigate to `http://localhost:5000` in your web browser to access the application. Users can interact with the platform to generate automated stock valuations and receive AI-driven insights into the models' results.

## License
Lucidity is released under the MIT License. See the LICENSE file for more details.
