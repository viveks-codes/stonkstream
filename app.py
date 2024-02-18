import streamlit as st
import os
import yfinance as yf
import mplfinance as mpf
from datetime import datetime, timedelta
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
import pandas as pd
import matplotlib
matplotlib.use('Agg') 

def plot_candlestick_to_pdf(symbol, start_date, end_date, interval='1h', emas=(10, 50, 100), pdf_pages=None):
    try:
        stock_data = yf.download(symbol, start=start_date, end=end_date, interval=interval)

        # Check if data is empty for the symbol
        if stock_data.empty:
            st.write(f"No data available for symbol: {symbol}")

            # Try fetching data with '.NS' extension
            symbol_with_ns = symbol + '.NS'
            stock_data_ns = yf.download(symbol_with_ns, start=start_date, end=end_date, interval=interval)

            if not stock_data_ns.empty:
                stock_data = stock_data_ns
                st.write(f"Using {symbol_with_ns} instead")
            else:
                st.write(f"No data available for {symbol_with_ns} as well")
                return

        # Calculate EMAs based on user input
        for ema in emas:
            stock_data[f'EMA{ema}'] = stock_data['Close'].ewm(span=ema, adjust=False).mean()

        # Plotting candlestick chart
        title = f'{symbol} Chart from {start_date} to {end_date} ({interval} interval) with {", ".join([f"{ema} EMA" for ema in emas])}'
        fig, axlist = mpf.plot(stock_data, type='candle', style='yahoo', title=title,
                               ylabel='Price', ylabel_lower='Volume', mav=emas, tight_layout=False, returnfig=True)

        # Add legends for EMA lines
        for ax in axlist:
            ax.legend(['Close'] + [f'EMA{ema}' for ema in emas])

        # Adjust layout to prevent tick label cutoff
        fig.subplots_adjust(bottom=0.2)  # You can adjust this value based on your specific case

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
    st.title("Candlestick Chart Generator")

    uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])

    if uploaded_file is not None:
        csv_file = uploaded_file
    else:
        csv_files = [f for f in os.listdir() if f.endswith('.csv')]

        if not csv_files:
            st.write("No CSV files found in the current directory.")
            return

        st.write("List of CSV files in the current directory:")
        for i, csv_file in enumerate(csv_files, start=1):
            st.write(f"{i}. {csv_file}")

        selected_index = st.number_input(f"Choose a CSV file (1-{len(csv_files)}): ", min_value=1, max_value=len(csv_files), value=1) - 1
        csv_file = csv_files[selected_index]

    default_start_date = (datetime.now() - timedelta(days=200)).strftime('%Y-%m-%d')
    start_date = parse_date_input(st.text_input(f"Enter start date (YYYY-MM-DD, default: {default_start_date}): ", value=default_start_date), default_start_date)
    end_date = parse_date_input(st.text_input(f"Enter end date (YYYY-MM-DD, default: {datetime.now().strftime('%Y-%m-%d')}): ", value=datetime.now().strftime('%Y-%m-%d')), datetime.now().strftime('%Y-%m-%d'))
    interval = st.text_input("Enter time interval (e.g., 1h, 1d, default: 1h): ", value='1h')
    emas_input = st.text_input("Enter a space-separated list of EMAs (default: 10 50 100): ", value='10 50 100')
    emas = parse_emas_input(emas_input)
    output_file = st.text_input("Enter output PDF file name (default: 'candlestick_charts_all_symbols.pdf'): ", value='candlestick_charts_all_symbols.pdf')

    if st.button("Generate PDF"):
        st.write("\nGenerating PDF...")
        pdf_pages_candlestick = PdfPages(output_file)

        # Read stock symbols from the chosen CSV file
        symbols_df = pd.read_csv(csv_file)
        symbols = symbols_df['Symbol'].tolist()

        # Loop through each symbol and plot candlestick chart
        for symbol in symbols:
            plot_candlestick_to_pdf(symbol, start_date=start_date, end_date=end_date,
                                    interval=interval, emas=emas, pdf_pages=pdf_pages_candlestick)

        # Close the PDF file for candlestick charts
        pdf_pages_candlestick.close()
        st.write("PDF generation complete.")

        # Provide download link for the generated PDF
        st.markdown(f"Download your PDF [here](./pages/{output_file})")

if __name__ == "__main__":
    main()
