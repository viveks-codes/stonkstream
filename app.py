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

def plot_candlestick_to_pdf(symbol, start_date, end_date, interval='1h', emas=(10, 50, 100), pdf_pages=None):
    try:
        stock_data = yf.download(symbol, start=start_date, end=end_date, interval=interval)

        # Check if data is empty for the symbol
        if stock_data.empty:
            # st.write(f"No data available for symbol: {symbol}")

            # Try fetching data with '.NS' extension
            symbol_with_ns = symbol + '.NS'
            stock_data_ns = yf.download(symbol_with_ns, start=start_date, end=end_date, interval=interval)

            if not stock_data_ns.empty:
                stock_data = stock_data_ns
                # st.write(f"Using {symbol_with_ns} instead")
            else:
                st.write(f"No data available for {symbol_with_ns}")
                return

        # Calculate EMAs based on user input
        for ema in emas:
            stock_data[f'EMA{ema}'] = stock_data['Close'].ewm(span=ema, adjust=False).mean()

        # Plotting candlestick chart
        title = f'\n{symbol} {start_date} to {end_date} ({interval} interval),\n {", ".join([f"{ema} EMA" for ema in emas])}'
        fig, axlist = mpf.plot(stock_data, type='candle', style='yahoo', title=title,
                               ylabel='Price', ylabel_lower='Volume', mav=emas, tight_layout=False, returnfig=True)

        # Add legends for EMA lines
        for ax in axlist:
            ax.legend(['Close'] + [f'EMA{ema}' for ema in emas])

        # Adjust layout to prevent tick label cutoff

        # Save the current candlestick chart plot to the PDF file
        pdf_pages.savefig(fig)
        plt.close(fig)

    except Exception as e:
        st.write(f"Error processing symbol {symbol}: {str(e)}")

def parse_emas_input(input_string):
    if not input_string.strip():  # If the input is empty, use default values
        return [10, 50, 100]

    return list(map(int, input_string.split()))

def parse_date_input(date_string, default_date):
    try:
        return pd.to_datetime(date_string).strftime('%Y-%m-%d')
    except ValueError:
        st.write(f"Invalid date format. Using default date: {default_date}")
        return default_date

def main():
    st.title("Application Switcher")

    app_selection = st.radio("Select an application:", ("Candlestick Chart Generator with EMAs", "Trend Line support and resistance"))

    if app_selection == "Candlestick Chart Generator with EMAs":
        generate_candlestick_chart()
    elif app_selection == "Trend Line support and resistance":
        st.markdown("[Other Application Link](https://linestream-aa4eid2emajwwpt4ogv4ns.streamlit.app/)")

import time

def generate_candlestick_chart():
    st.sidebar.title("Candlestick Chart Generator")

    uploaded_file = st.sidebar.file_uploader("Upload CSV file", type=["csv"])

    if uploaded_file is not None:
        csv_file = uploaded_file
    else:
        csv_files = [f for f in os.listdir() if f.endswith('.csv')]

        if not csv_files:
            st.sidebar.write("No CSV files found in the current directory.")
            return

        st.sidebar.write("List of CSV files in the current directory:")
        for i, csv_file in enumerate(csv_files, start=1):
            st.sidebar.write(f"{i}. {csv_file}")

        selected_index = st.sidebar.number_input(f"Choose a CSV file (1-{len(csv_files)}): ", min_value=1, max_value=len(csv_files), value=1) - 1
        csv_file = csv_files[selected_index]

    default_start_date = (datetime.now() - timedelta(days=200)).strftime('%Y-%m-%d')
    start_date = parse_date_input(st.sidebar.text_input(f"Enter start date (YYYY-MM-DD, default: {default_start_date}): ", value=default_start_date), default_start_date)
    end_date = parse_date_input(st.sidebar.text_input(f"Enter end date (YYYY-MM-DD, default: {datetime.now().strftime('%Y-%m-%d')}): ", value=datetime.now().strftime('%Y-%m-%d')), datetime.now().strftime('%Y-%m-%d'))
    interval_options = ["1h", "2m", "5m", "15m", "30m", "60m", "90m", "1m", "1d", "5d", "1wk", "1mo", "3mo"]
    interval = st.sidebar.selectbox("Interval", interval_options)

    emas_input = st.sidebar.text_input("Enter a space-separated list of EMAs (default: 10 50 100): ", value='10 50 100')
    emas = parse_emas_input(emas_input)
    output_file = st.sidebar.text_input("Enter output PDF file name (default: 'candlestick_charts_all_symbols.pdf'): ", value='candlestick_charts_all_symbols.pdf')

    if st.sidebar.button("Generate PDF"):
        st.sidebar.write("\nGenerating PDF...")
        pdf_pages_candlestick = PdfPages(output_file)

        # Read stock symbols from the chosen CSV file
        symbols_df = pd.read_csv(csv_file)
        symbols = symbols_df['Symbol'].tolist()

        # Initialize progress bar
        progress_bar = st.progress(0)

        # Measure time for generating PDF
        start_time = time.time()
        duration_ms = 0.0000
        # Loop through each symbol and plot candlestick chart
        for i, symbol in enumerate(symbols):
            success = st.success(symbol)
            warning = st.warning(duration_ms)

            plot_candlestick_to_pdf(symbol, start_date=start_date, end_date=end_date,
                                    interval=interval, emas=emas, pdf_pages=pdf_pages_candlestick)
            end_time = time.time()

            # Update progress bar
            progress = (i + 1) / len(symbols)
            progress_bar.progress(progress)
            duration_ms = (end_time - start_time) * 1000
            
            success.empty()
            warning.empty()
        # Close the PDF file for candlestick charts
        pdf_pages_candlestick.close()
        st.write("PDF generation complete.")

        # Measure the time taken and show it in milliseconds


        # Provide download link for the generated PDF
        with open(output_file, "rb") as f:
            pdf_bytes = f.read()
        st.markdown(get_binary_file_downloader_html(output_file, 'PDF file'), unsafe_allow_html=True)

def get_binary_file_downloader_html(bin_file, file_label='File'):
    with open(bin_file, 'rb') as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="{os.path.basename(bin_file)}" style="text-decoration: none; padding: 10px 20px; background-color: #4CAF50; color: white; border-radius: 5px; border: none; cursor: pointer; font-size: 16px;">{file_label}</a>'
    return href

if __name__ == "__main__":
    main()
