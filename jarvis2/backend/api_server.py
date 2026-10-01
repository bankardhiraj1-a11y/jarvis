import json
from flask import Flask, jsonify

app = Flask(__name__)

@app.after_request
def add_cors_headers(response):
    """Add CORS headers to all responses."""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@app.route('/api/trade-book')
def get_trade_book():
    """Get trade book (executed trades and positions)."""
    try:
        with open('trade_book.json', 'r') as f:
            return jsonify(json.load(f))
    except:
        return jsonify({'trades': [], 'positions': {}, 'last_updated': None})

@app.route('/api/agent-status')
def get_agent_status():
    """Get live agent status."""
    try:
        with open('agent_status.json', 'r') as f:
            return jsonify(json.load(f))
    except:
        return jsonify({
            'STOCKS': {'status': 'IDLE', 'last_signal': None, 'last_update': None},
            'XAUUSD': {'status': 'IDLE', 'last_signal': None, 'last_update': None}
        })

@app.route('/api/health')
def health():
    """System health check."""
    return jsonify({'status': 'ok', 'service': 'jarvis-2-data-api'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False, threaded=True)
