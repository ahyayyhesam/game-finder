from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
from requests.exceptions import RequestException
from requests.utils import quote
import requests

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
        # Encode the game name for the URL
        encoded_name = quote(game_name)
        response = requests.get(f'https://gogunlocked.com/?s={encoded_name}')
        response.raise_for_status()

        # Parse search results
        soup = BeautifulSoup(response.text, 'html.parser')
        first_result = soup.select_one('.cover-item')

        if not first_result:
            return jsonify({'error': 'No results found'}), 404

        game_link = first_result.select_one('.cover-item-image a')['href']
        game_title = first_result.select_one('.cover-item-content__title a').text.strip()

        # Fetch download link
        game_page_response = requests.get(game_link)
        game_page_response.raise_for_status()
        game_page_soup = BeautifulSoup(game_page_response.text, 'html.parser')
        download_link = game_page_soup.select_one('a.btn-download')['href']

        # Save to database
        new_game = Game(
            title=game_title,
            link=game_link,
            download_link=download_link
        )
        db.session.add(new_game)
        db.session.commit()

        return jsonify({
            'title': game_title,
            'link': game_link,
            'downloadLink': download_link
        })
    except RequestException as e:
        return jsonify({'error': f'Network error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
