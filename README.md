# TQQQ Dashboard Alert System 📈

A serverless stock monitoring application designed for Google Cloud Run. It tracks **TQQQ** (ProShares UltraPro QQQ) price action, technical indicators, and sends a beautiful HTML dashboard email at market open.

## 🚀 Key Features

- **Automated Monitoring**: Scheduled to run via Cloud Scheduler at market open (9:30 AM ET).
- **Technical Indicators**:
  - **ret_63**: 63-day return percentage.
  - **RSI_21**: 21-day Relative Strength Index.
  - **SMA_150**: 150-day Simple Moving Average (Price vs. SMA status).
- **Visual Intelligence**: Generates 90-day trend charts for Price, RSI, and Returns using Matplotlib.
- **Premium HTML Email**: Desktop and mobile-responsive email dashboard with embedded charts (base64).
- **Market Aware**: Uses `pandas_market_calendars` to skip holidays and weekends automatically.

## 📊 Dashboard Preview

The email includes:
1. **Latest Price**: Large prominent display of current TQQQ price.
2. **Metric Grid**: `ret_63` and `RSI_21` with color-coded sentiment (Green/Red).
3. **SMA Status**: Quick indicator of whether the Open price is ABOVE or BELOW the 150-day SMA.
4. **Trend Charts**: 90-day historical charts for Price, Returns, and RSI.

## 🛠️ Tech Stack

- **Python 3.11**
- **Data**: `yfinance`, `pandas`
- **Charts**: `matplotlib`
- **Backend/Deployment**: `Flask`, `Gunicorn`, `Docker`, `Google Cloud Run`
- **Scheduling**: `Google Cloud Scheduler`

## ⚙️ Configuration

The app uses a `.env` file (local) or Google Secret Manager (Cloud) for sensitive credentials:

- `EMAIL_ADDRESS`: Your GMail address.
- `EMAIL_PASSWORD`: GMail App Password.
- `SMTP_SERVER`: Default is `smtp.gmail.com`.
- `SMTP_PORT`: Default is `587`.

Application constants can be found in `config.py`.

## 📦 Local Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run manually**:
   ```bash
   python main.py
   ```

3. **Test with custom price**:
   ```bash
   python main.py --test-open 55.00
   ```

## ☁️ Cloud Deployment

For detailed instructions on deploying to Google Cloud Run, setting up secrets, and configuring the scheduler, see [deploy.md](./deploy.md).

---
*Disclaimer: This application is for informational purposes only. Use at your own risk.*
