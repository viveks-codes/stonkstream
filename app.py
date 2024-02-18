import streamlit as st
import os
import yfinance as yf
import mplfinance as mpf
from datetime import datetime, timedelta
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
import pandas as pd
import base64 
import matplotlib
matplotlib.use('Agg') 

def fit_trendlines_high_low(high: np.array, low: np.array, close: np.array):
    x = np.arange(len(close))
    coefs = np.polyfit(x, close, 1)
    # coefs[0] = slope,  coefs[1] = intercept
    line_points = coefs[0] * x + coefs[1]
    upper_pivot = (high - line_points).argmax() 
    lower_pivot = (low - line_points).argmin() 
    
    support_coefs = optimize_slope(True, lower_pivot, coefs[0], low)
    resist_coefs = optimize_slope(False, upper_pivot, coefs[0], high)

    return (support_coefs, resist_coefs)
def check_trend_line(support: bool, pivot: int, slope: float, y: np.array):
    # compute sum of differences between line and prices, 
    # return negative val if invalid 
    
    # Find the intercept of the line going through pivot point with given slope
    intercept = -slope * pivot + y[pivot]
    line_vals = slope * np.arange(len(y)) + intercept
     
    diffs = line_vals - y
    
    # Check to see if the line is valid, return -1 if it is not valid.
    if support and diffs.max() > 1e-5:
        return -1.0
    elif not support and diffs.min() < -1e-5:
        return -1.0

    # Squared sum of diffs between data and line 
    err = (diffs ** 2.0).sum()
    return err;


def optimize_slope(support: bool, pivot:int , init_slope: float, y: np.array):
    
    # Amount to change slope by. Multiplyed by opt_step
    slope_unit = (y.max() - y.min()) / len(y) 
    
    # Optmization variables
    opt_step = 1.0
    min_step = 0.0001
    curr_step = opt_step # current step
    
    # Initiate at the slope of the line of best fit
    best_slope = init_slope
    best_err = check_trend_line(support, pivot, init_slope, y)
    assert(best_err >= 0.0) # Shouldn't ever fail with initial slope

    get_derivative = True
    derivative = None
    while curr_step > min_step:

        if get_derivative:
            # Numerical differentiation, increase slope by very small amount
            # to see if error increases/decreases. 
            # Gives us the direction to change slope.
            slope_change = best_slope + slope_unit * min_step
            test_err = check_trend_line(support, pivot, slope_change, y)
            derivative = test_err - best_err;
            
            # If increasing by a small amount fails, 
            # try decreasing by a small amount
            if test_err < 0.0:
                slope_change = best_slope - slope_unit * min_step
                test_err = check_trend_line(support, pivot, slope_change, y)
                derivative = best_err - test_err

            if test_err < 0.0: # Derivative failed, give up
                raise Exception("Derivative failed. Check your data. ")

            get_derivative = False

        if derivative > 0.0: # Increasing slope increased error
            test_slope = best_slope - slope_unit * curr_step
        else: # Increasing slope decreased error
            test_slope = best_slope + slope_unit * curr_step
        

        test_err = check_trend_line(support, pivot, test_slope, y)
        if test_err < 0 or test_err >= best_err: 
            # slope failed/didn't reduce error
            curr_step *= 0.5 # Reduce step size
        else: # test slope reduced error
            best_err = test_err 
            best_slope = test_slope
            get_derivative = True # Recompute derivative
    
    # Optimize done, return best slope and intercept
    return (best_slope, -best_slope * pivot + y[pivot])


def fit_trendlines_single(data: np.array):
    # find line of best fit (least squared) 
    # coefs[0] = slope,  coefs[1] = intercept 
    x = np.arange(len(data))
    coefs = np.polyfit(x, data, 1)

    # Get points of line.
    line_points = coefs[0] * x + coefs[1]

    # Find upper and lower pivot points
    upper_pivot = (data - line_points).argmax() 
    lower_pivot = (data - line_points).argmin() 
   
    # Optimize the slope for both trend lines
    support_coefs = optimize_slope(True, lower_pivot, coefs[0], data)
    resist_coefs = optimize_slope(False, upper_pivot, coefs[0], data)

    return (support_coefs, resist_coefs) 





def analyze_symbol(symbol_name: str,  lookback=30, start=None, end=None, interval='1d'):
    data = yf.download(symbol_name, start=start, end=end, interval=interval)
    if data.empty:
        raise ValueError("No data available for the specified symbol and date range.")
    support_slope = [np.nan] * len(data)
    resist_slope = [np.nan] * len(data)
    for i in range(lookback - 1, len(data)):
        candles = data.iloc[i - lookback + 1: i + 1]
        support_coefs, resist_coefs = fit_trendlines_high_low(candles['High'], candles['Low'], candles['Close'])
        support_slope[i] = support_coefs[0]
        resist_slope[i] = resist_coefs[0]

    data['support_slope'] = support_slope
    data['resist_slope'] = resist_slope

    candles = data.iloc[-lookback:] # Last 30 candles in data
    support_coefs_c, resist_coefs_c = fit_trendlines_single(candles['Close'])
    support_coefs, resist_coefs = fit_trendlines_high_low(candles['High'], candles['Low'], candles['Close'])

    support_line_c = support_coefs_c[0] * np.arange(len(candles)) + support_coefs_c[1]
    resist_line_c = resist_coefs_c[0] * np.arange(len(candles)) + resist_coefs_c[1]

    support_line = support_coefs[0] * np.arange(len(candles)) + support_coefs[1]
    resist_line = resist_coefs[0] * np.arange(len(candles)) + resist_coefs[1]

    plt.style.use('dark_background')
    ax = plt.gca()

    def get_line_points(candles, line_points):
        idx = candles.index
        line_i = len(candles) - len(line_points)
        assert(line_i >= 0)
        points = []
        for i in range(line_i, len(candles)):
            points.append((idx[i], line_points[i - line_i]))
        return points

    s_seq = get_line_points(candles, support_line)
    r_seq = get_line_points(candles, resist_line)
    s_seq2 = get_line_points(candles, support_line_c)
    r_seq2 = get_line_points(candles, resist_line_c)
    mpf.plot(candles, alines=dict(alines=[s_seq, r_seq, s_seq2, r_seq2], colors=['w', 'w', 'b', 'b']), type='candle', style='charles', ax=ax)

    return ax

# Function definitions for fitting trendlines and optimizing slope remain unchanged

# Streamlit app UI
st.title("Symbol Analysis PDF Generator")

# File uploader for symbol list
st.sidebar.title("Upload Symbol List")
file_uploaded = st.sidebar.file_uploader("Upload CSV file", type=['csv'])

if file_uploaded is not None:
    symbols_df = pd.read_csv(file_uploaded)
    symbols_list = symbols_df['Symbol'].tolist()

    # Date selection
    st.sidebar.title("Date Range Selection")
    start_date = st.sidebar.date_input("Start Date", pd.to_datetime("2023-01-01"))
    end_date = st.sidebar.date_input("End Date",datetime.now().strftime('%Y-%m-%d'))

    # Interval selection
    interval_options = ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"]
    interval = st.sidebar.selectbox("Interval", interval_options)

    # Loopback selection
    lookback = st.sidebar.number_input("Loopback Period", min_value=1, max_value=365, value=30)

    # Generate PDF button
    if st.sidebar.button("Generate PDF"):
        with PdfPages('symbols_analysis.pdf') as pdf:
            for symbol in symbols_list:
                fig, ax = plt.subplots()
                ax = analyze_symbol(symbol+'.ns',lookback=lookback, start=start_date, end=end_date, interval=interval)
                plt.title(symbol)
                pdf.savefig(fig)
                plt.close()

        st.sidebar.success("PDF generated successfully.")

        # Provide download link for the generated PDF
        with open('symbols_analysis.pdf', 'rb') as f:
            pdf_contents = f.read()
        b64 = base64.b64encode(pdf_contents).decode()
        href = f'<a href="data:application/octet-stream;base64,{b64}" download="symbols_analysis.pdf">Download PDF</a>'
        st.markdown(href, unsafe_allow_html=True)

        # Remove the PDF file after providing download link
        os.remove('symbols_analysis.pdf')
