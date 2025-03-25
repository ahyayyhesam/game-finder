from flask import Flask, request, jsonify, send_from_directory
import requests
from bs4 import BeautifulSoup
import os

app = Flask(__name__)

# Serve the index.html file for the root route
@app.route('/')
def index():
    return send_from_directory(os.getcwd(), 'index.html')

@app.route('/search', methods=['GET'])
def search():
    game_name = request.args.get('game')
    try:
        # Fetch the HTML from GOG Unlocked
        response = requests.get(f'https://gogunlocked.com/?s={game_name}')
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract the first search result
        first_result = soup.select_one('.cover-item')
        game_link = first_result.select_one('.cover-item-image a')['href'] if first_result else 'Not Found'
        game_title = first_result.select_one('.cover-item-content__title a').text.strip() if first_result else 'No Title Found'

        download_link = 'Not Found'
        if game_link != 'Not Found':
            # Fetch the game's page to extract the download link
            game_page_response = requests.get(game_link)
            game_page_soup = BeautifulSoup(game_page_response.text, 'html.parser')
            download_link = game_page_soup.select_one('a.btn-download')['href'] if game_page_soup.select_one('a.btn-download') else 'Not Found'

        # Return the data as JSON
        return jsonify({
            'title': game_title,
            'link': game_link,
            'downloadLink': download_link,
        })
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': 'Failed to fetch results from GOG Unlocked'}), 500

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))  # Default to 5000 if PORT is not set  
    app.run(host="0.0.0.0", port=port)
