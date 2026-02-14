import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import pytz
import pandas_market_calendars as mcal
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for server
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import io
import base64
import config
import requests
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

def is_market_active():
    """
    Checks if the NYSE is open today (based on US/Eastern time).
    Returns True if today is a trading day, False otherwise.
    """
    try:
        # Get current time in US/Eastern
        est = pytz.timezone('US/Eastern')
        now = datetime.now(est)
        today_date = now.date()

        # check for weekend
        if now.weekday() >= 5: # 5=Sat, 6=Sun
            logging.info(f"Today {today_date} is a weekend. Market closed.")
            return False

        # Check for holidays using NYSE calendar
        nyse = mcal.get_calendar('NYSE')
        schedule = nyse.schedule(start_date=today_date, end_date=today_date)
        
        if schedule.empty:
            logging.info(f"Today {today_date} is a market holiday. Market closed.")
            return False
            
        logging.info(f"Today {today_date} is a valid trading day.")
        return True
    except Exception as e:
        logging.error(f"Error checking market calendar: {e}")
        # Fail safe: preserve original behavior (try to fetch data) if this check fails
        return True

def fetch_data(ticker_symbol=config.TICKER_SYMBOL, period="2y"):
    """
    Fetches historical data for the given ticker.
    Fetches 2 years of data for dashboard visualizations.
    Uses retry logic to handle rate limits.
    """
    logging.info(f"Fetching data for {ticker_symbol}...")
    
    max_retries = 3
    retry_delay = 5  # seconds

    for attempt in range(max_retries):
        try:
            # yfinance now uses curl_cffi internally to handle Yahoo's TLS fingerprinting.
            # Providing a standard requests session can cause failures.
            data = yf.download(
                ticker_symbol, 
                period=period, 
                interval="1d", 
                progress=False
            )
            
            if data is not None and not data.empty:
                return data
            
            logging.warning(f"Attempt {attempt + 1}: No data found for {ticker_symbol}. Retrying...")
            
        except Exception as e:
            logging.error(f"Attempt {attempt + 1}: Error fetching data: {e}")
            if "Rate limited" in str(e) or "Too Many Requests" in str(e):
                logging.warning(f"Rate limit detected. Waiting {retry_delay}s before retry...")
            
        if attempt < max_retries - 1:
            time.sleep(retry_delay)
            retry_delay *= 2  # Exponential backoff

    logging.error(f"Failed to fetch data for {ticker_symbol} after {max_retries} attempts.")
    return None



def get_close_prices(data):
    """Extract close prices from dataframe, handling MultiIndex columns."""
    if isinstance(data.columns, pd.MultiIndex):
        if config.TICKER_SYMBOL in data['Close'].columns:
            return data['Close'][config.TICKER_SYMBOL]
        else:
            return data['Close'].iloc[:, 0]
    return data['Close']

def calculate_sma(data, window=config.SMA_WINDOW):
    """
    Calculates the Simple Moving Average (SMA) for the given window.
    """
    if len(data) < window:
        logging.warning(f"Not enough data to calculate SMA {window}. Have {len(data)} rows.")
        return None
    
    try:
        close_prices = get_close_prices(data)
        sma = close_prices.rolling(window=window).mean()
        return sma
    except Exception as e:
        logging.error(f"Error calculating SMA: {e}")
        return None

def calculate_return_63(data):
    """
    Calculates the 63-day return (ret_63) as a percentage.
    """
    try:
        close_prices = get_close_prices(data)
        if len(close_prices) < config.RET_WINDOW:
            logging.warning(f"Not enough data to calculate {config.RET_WINDOW}-day return.")
            return None
        
        # Current price vs price 63 days ago
        current_price = float(close_prices.iloc[-1])
        past_price = float(close_prices.iloc[-config.RET_WINDOW])
        ret_63 = ((current_price - past_price) / past_price) * 100
        
        logging.info(f"ret_63 calculated: {ret_63:.2f}%")
        return ret_63
    except Exception as e:
        logging.error(f"Error calculating ret_63: {e}")
        return None

def calculate_rolling_return_63(data):
    """
    Calculates rolling 63-day returns for the entire series.
    """
    try:
        close_prices = get_close_prices(data)
        ret_63_series = close_prices.pct_change(periods=config.RET_WINDOW) * 100
        return ret_63_series
    except Exception as e:
        logging.error(f"Error calculating rolling ret_63: {e}")
        return None

def calculate_rsi(data, window=config.RSI_WINDOW):
    """
    Calculates the Relative Strength Index (RSI) for the given window.
    """
    try:
        close_prices = get_close_prices(data)
        if len(close_prices) < window + 1:
            logging.warning(f"Not enough data to calculate RSI {window}.")
            return None
        
        # Calculate price changes
        delta = close_prices.diff()
        
        # Separate gains and losses
        gains = delta.where(delta > 0, 0.0)
        losses = (-delta).where(delta < 0, 0.0)
        
        # Calculate average gains and losses using exponential moving average
        avg_gain = gains.ewm(com=window - 1, min_periods=window).mean()
        avg_loss = losses.ewm(com=window - 1, min_periods=window).mean()
        
        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        current_rsi = float(rsi.iloc[-1])
        logging.info(f"RSI_{window} calculated: {current_rsi:.2f}")
        return current_rsi
    except Exception as e:
        logging.error(f"Error calculating RSI: {e}")
        return None

def calculate_rolling_rsi(data, window=config.RSI_WINDOW):
    """
    Calculates rolling RSI for the entire series.
    """
    try:
        close_prices = get_close_prices(data)
        delta = close_prices.diff()
        gains = delta.where(delta > 0, 0.0)
        losses = (-delta).where(delta < 0, 0.0)
        avg_gain = gains.ewm(com=window - 1, min_periods=window).mean()
        avg_loss = losses.ewm(com=window - 1, min_periods=window).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    except Exception as e:
        logging.error(f"Error calculating rolling RSI: {e}")
        return None

def generate_chart(dates, values, title, color, y_label, reference_lines=None):
    """
    Generate a trend chart and return as base64 encoded image.
    
    Args:
        dates: List of dates
        values: List of values
        title: Chart title
        color: Line color
        y_label: Y-axis label
        reference_lines: Optional list of (y_value, color, label) tuples for horizontal lines
    """
    try:
        fig, ax = plt.subplots(figsize=(6, 2.5), dpi=100)
        
        # Style
        fig.patch.set_facecolor('#ffffff')
        ax.set_facecolor('#f8f9fa')
        
        # Plot the line
        ax.plot(dates, values, color=color, linewidth=2, alpha=0.9)
        ax.fill_between(dates, values, alpha=0.1, color=color)
        
        # Add reference lines if provided
        if reference_lines:
            for y_val, line_color, label in reference_lines:
                ax.axhline(y=y_val, color=line_color, linestyle='--', linewidth=1, alpha=0.7)

        # Dynamic y-axis: fit to data range with padding instead of including 0
        y_min, y_max = min(values), max(values)
        if reference_lines:
            ref_vals = [y_val for y_val, _, _ in reference_lines]
            y_min = min(y_min, *ref_vals)
            y_max = max(y_max, *ref_vals)
        y_padding = (y_max - y_min) * 0.1 if y_max != y_min else 1
        ax.set_ylim(y_min - y_padding, y_max + y_padding)

        # Formatting
        ax.set_title(title, fontsize=12, fontweight='600', color='#212529', pad=10)
        ax.set_ylabel(y_label, fontsize=9, color='#6c757d')
        
        # Date formatting
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
        plt.xticks(rotation=45, fontsize=8, color='#6c757d')
        plt.yticks(fontsize=8, color='#6c757d')
        
        # Grid
        ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#dee2e6')
        ax.spines['bottom'].set_color('#dee2e6')
        
        plt.tight_layout()
        
        # Convert to base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', bbox_inches='tight', facecolor='white', edgecolor='none')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        plt.close(fig)
        
        return image_base64
    except Exception as e:
        logging.error(f"Error generating chart: {e}")
        return None

def generate_trend_charts(data, days=90):
    """
    Generate all trend charts for the last N days.
    Returns dict with base64 encoded chart images.
    """
    charts = {}
    
    close_prices = get_close_prices(data)
    
    # Get last 90 days of data
    recent_data = data.tail(days)
    recent_close = close_prices.tail(days)
    dates = recent_data.index.tolist()
    
    # 1. TQQQ Price Chart
    price_values = recent_close.values.flatten()
    charts['price'] = generate_chart(
        dates, price_values,
        f'TQQQ Price (Last {days} Days)', '#2d5a87', 'Price ($)'
    )
    
    # 2. ret_63 Chart
    ret_63_series = calculate_rolling_return_63(data)
    if ret_63_series is not None:
        ret_values = ret_63_series.tail(days).values.flatten()
        charts['ret_63'] = generate_chart(
            dates, ret_values,
            f'ret_63 - 63-Day Return (Last {days} Days)', '#28a745', 'Return (%)',
            reference_lines=[(0, '#6c757d', 'Zero')]
        )
    
    # 3. RSI_21 Chart
    rsi_series = calculate_rolling_rsi(data)
    if rsi_series is not None:
        rsi_values = rsi_series.tail(days).values.flatten()
        charts['rsi_21'] = generate_chart(
            dates, rsi_values,
            f'RSI_21 - 21-Day RSI (Last {days} Days)', '#fd7e14', 'RSI',
            reference_lines=[(70, '#dc3545', 'Overbought'), (30, '#28a745', 'Oversold')]
        )
    
    return charts

def get_dashboard_metrics(data):
    """
    Calculate all TQQQ dashboard metrics.
    Returns a dictionary with all metrics.
    """
    close_prices = get_close_prices(data)
    
    latest_date = data.index[-1].strftime('%Y-%m-%d')
    latest_price = float(close_prices.iloc[-1])
    ret_63 = calculate_return_63(data)
    rsi_21 = calculate_rsi(data, config.RSI_WINDOW)
    sma_150 = float(calculate_sma(data).iloc[-1]) if calculate_sma(data) is not None else None
    
    # Get the open price
    if isinstance(data.columns, pd.MultiIndex):
        current_open = float(data['Open'][config.TICKER_SYMBOL].iloc[-1]) if config.TICKER_SYMBOL in data['Open'].columns else float(data['Open'].iloc[-1].item())
    else:
        current_open = float(data['Open'].iloc[-1])
    
    # Determine SMA status
    if sma_150:
        if current_open > sma_150:
            sma_status = "ABOVE"
        elif current_open < sma_150:
            sma_status = "BELOW"
        else:
            sma_status = "EQUAL"
    else:
        sma_status = "N/A"
    
    return {
        'latest_date': latest_date,
        'latest_price': latest_price,
        'current_open': current_open,
        'ret_63': ret_63,
        'rsi_21': rsi_21,
        'sma_150': sma_150,
        'sma_status': sma_status
    }

def check_condition(data, sma_series):
    """
    Checks if today's Open is above or below the previous day's SMA 150.
    Returns a tuple: (status, current_open, sma_value)
    message can be "ABOVE", "BELOW", or None.
    """
    try:
        last_sma = sma_series.iloc[-1]
        
        current_open = None
        if isinstance(data.columns, pd.MultiIndex):
             current_open = data['Open'][config.TICKER_SYMBOL].iloc[-1] if config.TICKER_SYMBOL in data['Open'].columns else data['Open'].iloc[-1].item()
        else:
             current_open = data['Open'].iloc[-1]

        # Convert to native float for comparison
        current_open = float(current_open)
        last_sma = float(last_sma)
        
        last_date = data.index[-1]
        logging.info(f"Latest Date: {last_date}")
        logging.info(f"Current Open: {current_open:.2f}")
        logging.info(f"SMA {config.SMA_WINDOW}: {last_sma:.2f}")

        if current_open > last_sma:
            return "ABOVE", current_open, last_sma
        elif current_open < last_sma:
            return "BELOW", current_open, last_sma
        else:
            return "EQUAL", current_open, last_sma

    except Exception as e:
        logging.error(f"Error checking condition: {e}")
        return None, None, None

def generate_html_email(metrics, charts=None):
    """
    Generate a beautiful HTML email with TQQQ dashboard metrics and trend charts.
    """
    # Determine colors based on values
    ret_color = "#28a745" if metrics['ret_63'] and metrics['ret_63'] > 0 else "#dc3545"
    
    # RSI zones: <30 oversold (green buy zone), >70 overbought (red sell zone), 30-70 neutral
    if metrics['rsi_21']:
        if metrics['rsi_21'] < 30:
            rsi_color = "#28a745"  # Green - Oversold
            rsi_zone = "Oversold"
        elif metrics['rsi_21'] > 70:
            rsi_color = "#dc3545"  # Red - Overbought
            rsi_zone = "Overbought"
        else:
            rsi_color = "#ffc107"  # Yellow - Neutral
            rsi_zone = "Neutral"
    else:
        rsi_color = "#6c757d"
        rsi_zone = "N/A"
    
    # SMA status color
    sma_color = "#28a745" if metrics['sma_status'] == "ABOVE" else "#dc3545" if metrics['sma_status'] == "BELOW" else "#6c757d"
    
    # Build chart HTML sections
    charts_html = ""
    if charts:
        if charts.get('price'):
            charts_html += f'''
            <div style="padding: 15px 20px;">
                <img src="data:image/png;base64,{charts['price']}" alt="TQQQ Price Chart" style="width: 100%; max-width: 560px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            </div>
            '''
        if charts.get('ret_63'):
            charts_html += f'''
            <div style="padding: 15px 20px;">
                <img src="data:image/png;base64,{charts['ret_63']}" alt="ret_63 Chart" style="width: 100%; max-width: 560px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            </div>
            '''
        if charts.get('rsi_21'):
            charts_html += f'''
            <div style="padding: 15px 20px;">
                <img src="data:image/png;base64,{charts['rsi_21']}" alt="RSI_21 Chart" style="width: 100%; max-width: 560px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            </div>
            '''
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>TQQQ Dashboard</title>
    </head>
    <body style="margin: 0; padding: 20px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f8f9fa;">
        
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); overflow: hidden;">
            
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%); color: white; padding: 30px; text-align: center;">
                <h1 style="margin: 0; font-size: 28px; font-weight: 600;">TQQQ Dashboard</h1>
                <p style="margin: 10px 0 0 0; opacity: 0.9; font-size: 16px;">📅 {metrics['latest_date']}</p>
            </div>
            
            <!-- Price Section -->
            <div style="padding: 25px; text-align: center; border-bottom: 1px solid #e9ecef;">
                <p style="margin: 0; color: #6c757d; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">Latest Price</p>
                <h2 style="margin: 10px 0 0 0; font-size: 42px; font-weight: 700; color: #212529;">${metrics['latest_price']:.2f}</h2>
            </div>
            
            <!-- Metrics Grid -->
            <div style="padding: 20px;">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <!-- ret_63 -->
                        <td style="padding: 15px; text-align: center; width: 50%; vertical-align: top;">
                            <div style="background-color: #f8f9fa; border-radius: 8px; padding: 20px;">
                                <p style="margin: 0 0 5px 0; color: #6c757d; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;">ret_63</p>
                                <p style="margin: 0; font-size: 28px; font-weight: 700; color: {ret_color};">{metrics['ret_63']:.2f}%</p>
                                <p style="margin: 5px 0 0 0; color: #6c757d; font-size: 11px;">63-Day Return</p>
                            </div>
                        </td>
                        <!-- RSI_21 -->
                        <td style="padding: 15px; text-align: center; width: 50%; vertical-align: top;">
                            <div style="background-color: #f8f9fa; border-radius: 8px; padding: 20px;">
                                <p style="margin: 0 0 5px 0; color: #6c757d; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;">RSI_21</p>
                                <p style="margin: 0; font-size: 28px; font-weight: 700; color: {rsi_color};">{metrics['rsi_21']:.2f}</p>
                                <p style="margin: 5px 0 0 0; color: {rsi_color}; font-size: 11px;">{rsi_zone}</p>
                            </div>
                        </td>
                    </tr>
                </table>
            </div>
            
            <!-- SMA Status -->
            <div style="padding: 0 20px 20px 20px;">
                <div style="background-color: #f8f9fa; border-radius: 8px; padding: 20px; text-align: center;">
                    <p style="margin: 0 0 5px 0; color: #6c757d; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;">SMA 150 Status</p>
                    <p style="margin: 0; font-size: 24px; font-weight: 700; color: {sma_color};">{metrics['sma_status']}</p>
                    <p style="margin: 10px 0 0 0; color: #6c757d; font-size: 13px;">
                        Open: <strong>${metrics['current_open']:.2f}</strong> | SMA: <strong>${metrics['sma_150']:.2f}</strong>
                    </p>
                </div>
            </div>
            
            <!-- 90-Day Trend Charts Section -->
            <div style="padding: 10px 20px 5px 20px;">
                <h3 style="margin: 0; font-size: 16px; font-weight: 600; color: #212529;">� 90-Day Trends</h3>
            </div>
            
            {charts_html}
            
            <!-- Footer -->
            <div style="background-color: #f8f9fa; padding: 20px; text-align: center; border-top: 1px solid #e9ecef;">
                <p style="margin: 0; color: #6c757d; font-size: 12px;">Generated by StockAlert • TQQQ Dashboard</p>
            </div>
            
        </div>
        
    </body>
    </html>
    """
    return html

def send_email(subject, body, html_body=None):
    """
    Sends an email notification using credentials from config.
    Supports both plain text and HTML email formats.
    """
    if not config.EMAIL_ADDRESS or not config.EMAIL_PASSWORD:
        logging.error("Email credentials not set. Skipping email.")
        return

    msg = MIMEMultipart('alternative')
    msg['From'] = config.EMAIL_ADDRESS
    msg['To'] = config.TO_EMAIL
    msg['Subject'] = subject

    # Attach plain text version
    msg.attach(MIMEText(body, 'plain'))
    
    # Attach HTML version if provided
    if html_body:
        msg.attach(MIMEText(html_body, 'html'))

    try:
        logging.info("Connecting to SMTP server...")
        server = smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT)
        server.starttls()
        server.login(config.EMAIL_ADDRESS, config.EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        logging.info(f"Email sent to {config.TO_EMAIL}")
    except Exception as e:
        logging.error(f"Failed to send email: {e}")
