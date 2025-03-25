from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
from requests.exceptions import RequestException
from requests.utils import quote

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///games.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    link = db.Column(db.String(255))
    download_link = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, server_default=db.func.now())

class RequestLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_ip = db.Column(db.String(45))  # For IPv4 addresses
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Initialize database
with app.app_context():
    db.create_all()

# Rate Limiting Function
def is_rate_limited():
    client_ip = request.remote_addr
    one_minute_ago = datetime.utcnow() - timedelta(minutes=1)
    recent_requests = RequestLog.query.filter(
        RequestLog.client_ip == client_ip,
        RequestLog.timestamp >= one_minute_ago
    ).count()
    
    if recent_requests >= 5:
        return True  # Over the limit
    
    # Log the new request
    new_log = RequestLog(client_ip=client_ip)
    db.session.add(new_log)
    db.session.commit()
    
    return False

@app.route('/')
def index():
    games = Game.query.order_by(Game.timestamp.desc()).all()
    return render_template('list.html', games=games)

@app.route('/search-ui')
def search_ui():
    return send_from_directory(os.getcwd(), 'index.html')

@app.route('/api/search', methods=['GET'])
def search():
    # Check rate limit first
    if is_rate_limited():
        return jsonify({'error': 'Too many requests. Try again in 1 minute.'}), 429

    game_name = request.args.get('game')
    if not game_name:
        return jsonify({'error': 'No game name provided'}), 400

    try:
        # ... (rest of your scraping logic remains the same) ...
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
