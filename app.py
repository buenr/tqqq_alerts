"""
Flask HTTP server for Cloud Run.
Cloud Scheduler will trigger the /run endpoint to execute stock alerts.
"""
import os
import logging
from flask import Flask, jsonify

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

app = Flask(__name__)


@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint for Cloud Run."""
    return jsonify({"status": "healthy", "service": "StockAlert"}), 200


@app.route('/run', methods=['GET', 'POST'])
def run_alert():
    """
    Execute the stock alert check.
    Called by Cloud Scheduler or manually via HTTP.
    """
    try:
        import main
        main.main()
        return jsonify({"status": "success", "message": "Stock alert check completed"}), 200
    except Exception as e:
        logging.error(f"Error running alert: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
