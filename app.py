from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from requests.exceptions import RequestException
from requests.utils import quote
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///games.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Database setup
db = SQLAlchemy(app)

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    link = db.Column(db.String(255))
    download_link = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, server_default=db.func.now())

# Rate limiter (5 requests per minute per IP)
limiter = Limiter(app, key_func=get_remote_address, default_limits=["5 per minute"])

# Initialize database
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    # Fetch all games from the database
    games = Game.query.order_by(Game.timestamp.desc()).all()
    return render_template('list.html', games=games)

@app.route('/search-ui')
def search_ui():
    return send_from_directory(os.getcwd(), 'index.html')

@app.route('/api/search', methods=['GET'])
@limiter.limit("5/minute")  # Apply rate limit
def search():
    game_name = request.args.get('game')
    if not game_name:
        return jsonify({'error': 'No game name provided'}), 400

    try:
        encoded_name = quote(game_name)
        response = requests.get(f'https://gogunlocked.com/?s={encoded_name}')
        response.raise_for_status()

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
