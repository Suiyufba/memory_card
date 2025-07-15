from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
import json
import random

app = Flask(__name__, template_folder='../html')
CARDS_FILE = os.path.join(os.path.dirname(__file__), '../cards.json')

def load_cards():
    if not os.path.exists(CARDS_FILE):
        return []
    with open(CARDS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_cards(cards):
    with open(CARDS_FILE, 'w', encoding='utf-8') as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/add', methods=['POST'])
def add_card():
    title = request.form.get('title')
    content = request.form.get('content')
    if not title or not content:
        return redirect(url_for('index'))
    cards = load_cards()
    card = {
        'id': len(cards),
        'title': title,
        'content': content
    }
    cards.append(card)
    save_cards(cards)
    return redirect(url_for('index'))

@app.route('/draw', methods=['GET'])
def draw_card():
    cards = load_cards()
    if not cards:
        return jsonify({'success': False, 'message': 'No cards found, please add some first!'})
    card = random.choice(cards)
    return jsonify({'success': True, 'id': card['id'], 'title': card['title']})

@app.route('/reveal/<int:card_id>', methods=['GET'])
def reveal_card(card_id):
    cards = load_cards()
    for card in cards:
        if card['id'] == card_id:
            return jsonify({'success': True, 'content': card['content']})
    return jsonify({'success': False, 'message': 'Card not found'})

if __name__ == '__main__':
    app.run(debug=True) 