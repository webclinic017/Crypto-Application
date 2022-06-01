"""Crypto Linear Regression App by Peter Lieberman"""

# Loads basic libraries and dependencies
from PIL import Image
import pandas as pd
import numpy as np
import datetime as dt
import os
import financialanalysis as fa
import streamlit as st
from messari.messari import Messari
import alpaca_trade_api as tradeapi
import matplotlib.pyplot as plt
import hvplot.pandas
import holoviews as hv
import plotly.graph_objects as go
from plotly.subplots import make_subplots
hv.extension('bokeh')

# API keys & Streamlit secrerts
messari_api_key = messari_api_key = st.secrets["MESSARI_API_KEY"]# Insert your Messari API private key into a Streamlit secrets file 
messari = Messari(messari_api_key) # A paid subscription to Messari API is required

alpaca_api_key = st.secrets["ALPACA_API_KEY"]
alpaca_secret_key = st.secrets["ALPACA_SECRET_KEY"]

# Application Page Configuration: Headers & Sidebar #

st.set_option('deprecation.showPyplotGlobalUse', False)
st.header('Crypto Asset Analytics')

st.markdown("""
This app connects to crypto APIs and runs a series of models 
to assess past performance and predict future price trends!
* **Python libraries:** pandas, numpy, os, streamlit, messari.messari, financialanalysis, scikit-learn
* **Data source:** [Messari.io](https://messari.io/api)
* **Models:** linear regression, risk/return analysis, and statistical correlations
* **Charts:** all charts are interactive and can be saved as images
""")


# Sidebar widgets: cryptocurrency and time period selection
st.sidebar.header('User Input Features')
st.sidebar.caption('Select a crypto asset and the number of historical months to include in your analysis.')


# Widget to select cryptocurrency
cryptocurrencies = ['Bitcoin', 'Ethereum', 'Cardano', 
                    'Solana','Avalanche', 'Polkadot', 'Polygon',
                    'NEAR', 'Algorand', 'Cosmos', 
                    'Fantom','Mina', 'Celo']

selected_asset = st.sidebar.selectbox('Cryptocurrency', cryptocurrencies)

# Widget to select timeperiod
number_of_months = st.sidebar.slider('Number of Months', value=6, min_value=1, max_value=60)
start_date = pd.to_datetime("today") - pd.DateOffset(months=number_of_months)
end_date = pd.to_datetime("today")


# Analytics Section 1: Function for Linear Regressions #

st.markdown("""**Linear Regression Channel**""")
st.markdown("""Regression line of time and price with standard deviation channels and Simple Moving Averages.""")


def get_timeseries_data(asset, start, end):

    # API pull from Messari for timeseries price data
    price_data = messari.get_metric_timeseries(asset_slugs=asset, asset_metric = "price", start=start, end=end)
    
    # Filters the data to capture the closing price only
    price_data = pd.DataFrame(price_data[asset]['close'])
    price_data = price_data.rename(columns={"close" : "Price"})
    price_data.index.names = ['Date']
    
    # Function returns the daily returns, cumulative returns, and real price of the asset
    price_data["Daily Returns"] = price_data["Price"].pct_change()
    price_data["Cumulative Returns"] = (1 + price_data["Daily Returns"]).cumprod()

    price_data.dropna(inplace=True)
    return price_data

price_data = get_timeseries_data(selected_asset, start_date, end_date)

def timeseries_linear_regression(price_data, start, end):
    
    price_data = price_data.round(2)

    sma200 = price_data["Price"].rolling(window=200).mean()
    sma50 = price_data["Price"].rolling(window=50).mean()
    
    std = price_data["Cumulative Returns"].std()
    
    linear_regression_df = price_data
    linear_regression_df.reset_index(inplace=True)
    
    # Utilizes financialanalysis (fa) module to build linear regression channels
    X = linear_regression_df["Date"].to_list() # converts Series to list
    X = fa.datetimeToFloatyear(X) # for example, 2020-07-01 becomes 2020.49589041
    X = np.array(X) # converts list to a numpy array
    X = X[::,None] # converts row vector to column vector (just column vector is acceptable)
    y = linear_regression_df["Cumulative Returns"] # get y data (relative price)
    y = y.values # converts Series to numpy
    y = y[::,None] # row vector to column vector (just column vector is acceptable)
    
    slope, intercept, x, fittedline = fa.timeseriesLinearRegression(linear_regression_df["Date"], linear_regression_df["Cumulative Returns"])

    # Trendlines for standard deviation parallel channels
    fittedline_upper_1 = fittedline + std
    fittedline_lower_1 = fittedline - std
    fittedline_upper_2 = fittedline + (std*2)
    fittedline_lower_2 = fittedline - (std*2)
    
    chart = make_subplots(specs=[[{"secondary_y" : True}]])
    chart.add_trace(go.Scatter(x=linear_regression_df["Date"], y=linear_regression_df["Price"], name="Price", line_color="black"), secondary_y=True,)
    #chart.add_trace(go.Scatter(x=linear_regression_df["Date"], y=linear_regression_df["Cumulative Returns"], line_color="white", showlegend=False, hoverinfo='none'), secondary_y=True,)
    chart.add_trace(go.Scatter(x=linear_regression_df["Date"], y=fittedline, name="Prediction", line_color="lightslategray", hoverinfo='none'), secondary_y=False,)
    chart.add_trace(go.Scatter(x=linear_regression_df["Date"], y=fittedline_lower_1, name="Standard Deviation", line_color="forestgreen", hoverinfo='none'), secondary_y=False,)
    chart.add_trace(go.Scatter(x=linear_regression_df["Date"], y=fittedline_upper_1, line_color="forestgreen", showlegend=False, hoverinfo='none'), secondary_y=False,)
    chart.add_trace(go.Scatter(x=linear_regression_df["Date"], y=fittedline_lower_2, name="2 Standard Deviations", line_color="rosybrown", hoverinfo='none'), secondary_y=False,)
    chart.add_trace(go.Scatter(x=linear_regression_df["Date"], y=fittedline_upper_2, name="2 Standard Deviations", line_color="rosybrown", showlegend=False, hoverinfo='none'), secondary_y=False,)
    chart.add_trace(go.Scatter(x=linear_regression_df["Date"], y=sma200, name="200-Day SMA", line_color="gray"), secondary_y=True,)
    chart.add_trace(go.Scatter(x=linear_regression_df["Date"], y=sma50, name="50-Day SMA", line_color="lightgray"), secondary_y=True,)

    chart.update_xaxes(title_text = "Date", showline=False)
    chart.update_yaxes(title_text="Actual Price", range=[price_data["Price"].min() * .6, price_data["Price"].max() * 1.2], zeroline = True, tickformat = '$', showgrid=True, tick0 = 0, secondary_y=True)
    chart.update_yaxes(showticklabels = False, range=[price_data["Cumulative Returns"].min() * .6, price_data["Cumulative Returns"].max()* 1.2], tick0 = 0, secondary_y=False)
    chart.update_layout(template="simple_white")
    chart.update_traces(marker_colorscale="Earth", selector=dict(type='scatter'))
    chart.update_traces(fill="none")
    chart.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1, xanchor="left", x=.01, font = dict(size = 10, color = "black")))
    chart.update_layout(plot_bgcolor='white')
    chart.update_layout(margin=dict(l=0, r=0, t=55))
    chart.update_yaxes(nticks = 10, secondary_y=True)

    return st.plotly_chart(chart)

chart = timeseries_linear_regression(price_data, start_date, end_date)

# Function to pull timeseries price data for assets
# Feeds into functions that follow afterwards

today = pd.to_datetime("today")
one_year_ago = pd.to_datetime("today") - pd.DateOffset(years=1)

@st.cache
def get_timeseries_data(asset, start, end):

    # API pull from Messari for timeseries price data
    price_data = messari.get_metric_timeseries(asset_slugs=asset, asset_metric = "price", start=start, end=end)
    
    # Filters the data to capture the closing price only
    price_data = pd.DataFrame(price_data[asset]['close'])
    price_data = price_data.rename(columns={"close" : f"{asset} Price"})
    price_data.index.names = ['Date']
    
    # Function returns the daily returns, cumulative returns, and real price of the asset
    price_data[f"{asset} Daily Returns"] = price_data[f"{asset} Price"].pct_change()
    price_data[f"{asset} Cumulative Returns"] = (1 + price_data[f"{asset} Daily Returns"]).cumprod()

    price_data.dropna(inplace=True)
    return price_data

# Builds two DataFrames that combine data for all the assets
# First DataFrame shows the close price data
# Second DataFrame shows the cumulative returns data
@st.cache
def load_crypto_prices(start_date, end_date):
    
    bitcoin_df = get_timeseries_data('Bitcoin', start_date, end_date)
    ethereum_df = get_timeseries_data('Ethereum', start_date, end_date)
    cardano_df = get_timeseries_data('Cardano', start_date, end_date)
    solana_df = get_timeseries_data("Solana", start_date, end_date)
    avalanche_df = get_timeseries_data('Avalanche', start_date, end_date)
    polkadot_df = get_timeseries_data('Polkadot', start_date, end_date)
    polygon_df = get_timeseries_data('Polygon', start_date, end_date)
    cosmos_df = get_timeseries_data('Cosmos', start_date, end_date)
    algorand_df = get_timeseries_data('Algorand', start_date, end_date)
    near_df = get_timeseries_data('NEAR', start_date, end_date)
    fantom_df = get_timeseries_data('Fantom', start_date, end_date)
    mina_df = get_timeseries_data('Mina', start_date, end_date)
    celo_df = get_timeseries_data('Celo', start_date, end_date)

    crypto_returns = pd.concat([bitcoin_df["Bitcoin Cumulative Returns"], ethereum_df["Ethereum Cumulative Returns"],
        cardano_df["Cardano Cumulative Returns"], solana_df["Solana Cumulative Returns"], 
        avalanche_df["Avalanche Cumulative Returns"], polkadot_df["Polkadot Cumulative Returns"], polygon_df["Polygon Cumulative Returns"], 
        cosmos_df["Cosmos Cumulative Returns"], algorand_df["Algorand Cumulative Returns"], near_df["NEAR Cumulative Returns"], 
        fantom_df["Fantom Cumulative Returns"], mina_df["Mina Cumulative Returns"], celo_df["Celo Cumulative Returns"]], axis= "columns", join="inner")

    crypto_prices = pd.concat([bitcoin_df["Bitcoin Price"], ethereum_df["Ethereum Price"],
    cardano_df["Cardano Price"], solana_df["Solana Price"], 
    avalanche_df["Avalanche Price"], polkadot_df["Polkadot Price"], polygon_df["Polygon Price"], 
    cosmos_df["Cosmos Price"], algorand_df["Algorand Price"], near_df["NEAR Price"],
    fantom_df["Fantom Price"], mina_df["Mina Price"], celo_df["Celo Price"]], axis= "columns", join="inner")

    column_names = ["Bitcoin", "Ethereum", 
                    "Celo", "Cardano",
                    "Solana", "Avalanche", "Polkadot",
                    "Polygon", "Cosmos",
                    "Algorand", "NEAR", 
                    "Fantom", "Mina"]

    crypto_returns.columns = column_names
    crypto_prices.columns = column_names
    crypto_returns = crypto_returns.round(2)
    crypto_prices = crypto_prices.round(2)

    return crypto_returns, crypto_prices

crypto_returns, crypto_prices = load_crypto_prices(one_year_ago, today)

# Function to transform the number_of_months input into number_of_days
# "number_of_days" is used as the window to calculate the rolling correlations
def number_of_days(number_of_months):
    
    if number_of_months > 12:
        return 365
    
    else:
        return number_of_months * 30
    
number_of_days = number_of_days(number_of_months)


# Analytics Section 2: Function for Token Statistics & Performance #

risk_free_rate = .025 # necessary for Sortino/Sharpe Ratio calculations

# Function to display summary statistics and financial ratios
def get_token_statistics(asset, start, end, days):
    
    # API pull from Messari for timeseries price data
    price_data = messari.get_metric_timeseries(asset_slugs=asset, asset_metric = "price", start=start, end=end)

    # Filters the data to capture the closing price only
    price_data = pd.DataFrame(price_data[asset]['close'])
    price_data = price_data.rename(columns={"close" : asset})
    price_data.index.names = ['Date']
    price_data = price_data
    
    # Calculates average daily returns and cumulative returns of the asset
    daily_returns = pd.DataFrame(price_data.pct_change().dropna())
    cumulative_returns = pd.DataFrame((1 + daily_returns).cumprod())
    total_return = cumulative_returns.iloc[-1]
    peak = cumulative_returns.expanding(min_periods=1).max()
    ath = peak.max()

    # Calculates annualized returns / standard deviation, the variance, and max drawdown
    standard_deviation = daily_returns.std() * np.sqrt(days)
    max_drawdown = (cumulative_returns/peak-1).min()
    negative_standard_deviation = daily_returns[daily_returns<0].std() * np.sqrt(days)

    # Calculates the Sharpe, Sortino, & Calmar Ratios. Negative Annualized Standard Deviation is used for Sortino Ratio
    sharpe_ratio = (total_return - risk_free_rate) / standard_deviation
    sortino_ratio = (total_return - risk_free_rate) / negative_standard_deviation
    calmar_ratio = (total_return - risk_free_rate) / (abs(max_drawdown))

    # Combines three metrics into a single DataFrame
    alist = []
    alist.append(calmar_ratio)
    alist.append(sortino_ratio)
    alist.append(sharpe_ratio)
    alist.append(max_drawdown)
    alist.append(ath)
    alist.append(standard_deviation)
    alist.append(total_return)
    token_statistics = pd.DataFrame(alist).T
    token_statistics.columns = ["Calmar Ratio", "Sortino Ratio", "Sharpe Ratio", "Max Drawdown", "Peak", "Volatity", "Return"]
    token_statistics = token_statistics.round(2)

    return token_statistics

bar_chart = get_token_statistics(selected_asset, start_date, end_date, number_of_days).hvplot.bar(color="black", hover_color="green", rot=45)

st.markdown("""**Financial Ratios & Statistics**""")
st.markdown("""Risk/return metrics and performance ratios over selected time period.""")

st.bokeh_chart(hv.render(bar_chart, backend="bokeh"))

# Function to calculate the asset correlations
def crypto_correlations(asset, days):
    
    correlations = crypto_returns.tail(int(days)).corr() * crypto_returns.tail(int(days)).corr()
    correlation_asset = correlations[f"{asset}"]
    correlation_asset = correlation_asset.drop(columns={asset})
    
    correlation_asset = correlation_asset.round(2)

    correlation_asset = correlation_asset.sort_values(ascending=True)
    
    return correlation_asset


# Correlations heatmap
correlations = crypto_correlations(selected_asset, number_of_days)
correlations_plot = correlations.hvplot.heatmap(cmap="Greys", rot=45, xaxis=None)

st.markdown("""**Asset Correlations**""")
st.markdown("""Price correlation with other assets over the last 12 months.""")
st.latex("(r^2)")
st.bokeh_chart(hv.render(correlations_plot, backend="bokeh"))


# Calculating correlations with SPY, QQQ, ARKK over time period selected by user
alpaca = tradeapi.REST(alpaca_api_key, alpaca_secret_key, api_version="v3")

start = start_date.strftime("%Y-%m-%d")
today = end_date.strftime("%Y-%m-%d")
tickers = ["SPY", "QQQ", "ARKK"]
timeframe = "1D"

indices_df = alpaca.get_bars(tickers, timeframe, start = start, end = today ).df

spy_df = indices_df[indices_df['symbol']=='SPY'].drop('symbol', axis=1)
spy_df = pd.DataFrame(spy_df["close"])
spy_df = spy_df.rename(columns={"close": "SPY"})

qqq_df = indices_df[indices_df['symbol']=='QQQ'].drop('symbol', axis=1)
qqq_df = pd.DataFrame(qqq_df["close"])
qqq_df = qqq_df.rename(columns={"close": "QQQ"})

arkk_df = indices_df[indices_df['symbol']=='ARKK'].drop('symbol', axis=1)
arkk_df = pd.DataFrame(arkk_df["close"])
arkk_df = arkk_df.rename(columns={"close": "ARKK"})

stock_prices = pd.concat([spy_df, qqq_df , arkk_df],axis="columns", join="inner")
stock_prices.reset_index(inplace=True)
stock_prices = stock_prices.rename(columns={"timestamp": "Date"})
stock_prices["Date"] = stock_prices["Date"].dt.strftime('%Y-%m-%d')
stock_prices["Date"] = pd.to_datetime(stock_prices["Date"], infer_datetime_format=True)
stock_prices = stock_prices.set_index("Date")

daily_returns = stock_prices.pct_change().dropna()
cumulative_returns = (1 + daily_returns).cumprod()

spy_correlation = price_data["Cumulative Returns"].corr(cumulative_returns["SPY"]) * price_data["Cumulative Returns"].corr(cumulative_returns["SPY"]).round(2)
spy_correlation = spy_correlation.round(2)
qqq_correlation = price_data["Cumulative Returns"].corr(cumulative_returns["QQQ"]) * price_data["Cumulative Returns"].corr(cumulative_returns["QQQ"]).round(2)
qqq_correlation = qqq_correlation.round(2)
arkk_correlation = price_data["Cumulative Returns"].corr(cumulative_returns["ARKK"]) * price_data["Cumulative Returns"].corr(cumulative_returns["ARKK"]).round(2)
arkk_correlation = arkk_correlation.round(2)

st.sidebar.header('Stock Market Correlation')
st.sidebar.caption("Correlation with market indices over time period.")
#col1, col2, col3 = st.columns(3) # code to move indice correlation into main body of application
st.sidebar.metric("S&P 500 (SPY)", spy_correlation, delta_color="off")
st.sidebar.metric("NASDAQ (QQQ)", qqq_correlation, delta_color="off")
st.sidebar.metric("Ark Innovation Fund (ARKK)", arkk_correlation, delta_color="off")
