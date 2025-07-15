from flask import Flask, render_template, request, redirect, url_for, jsonify, session, send_file
import os
import json
import random
import time
from datetime import datetime, timedelta

app = Flask(__name__, template_folder='../html')
app.secret_key = 'memory_card_secret_key'
CARDS_FILE = os.path.join(os.path.dirname(__file__), '../cards.json')

# 艾宾浩斯遗忘曲线推荐复习间隔（单位：天）
EBBINGHAUS_INTERVALS = [0, 1, 2, 4, 7, 15, 30, 90, 180, 365]

def load_cards():
    if not os.path.exists(CARDS_FILE):
        return []
    with open(CARDS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_cards(cards):
    with open(CARDS_FILE, 'w', encoding='utf-8') as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if username == 'admin' and password == '123456':
        session['logged_in'] = True
        return jsonify({'success': True, 'message': '登录成功'})
    else:
        return jsonify({'success': False, 'message': '用户名或密码错误'})

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('logged_in', None)
    return jsonify({'success': True, 'message': '已登出'})

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return jsonify({'success': False, 'message': '请先登录'}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/', methods=['GET'])
def index():
    return send_file('../html/index.html')

@app.route('/add', methods=['POST'])
@login_required
def add_card():
    title = request.form.get('title')
    content = request.form.get('content')
    tags = request.form.get('tags', '')
    img = request.form.get('img', '')
    tag_list = [t.strip() for t in tags.split(',') if t.strip()]
    if not title or not content:
        return redirect(url_for('index'))
    cards = load_cards()
    now = int(time.time())
    card = {
        'id': len(cards),
        'title': title,
        'content': content,
        'tags': tag_list,
        'img': img,
        'review_count': 0,
        'next_review': now,  # 立即可复习
        'last_review': None,
        'interval_index': 0  # 当前在曲线第几步
    }
    cards.append(card)
    save_cards(cards)
    return redirect(url_for('index'))

@app.route('/draw', methods=['GET'])
@login_required
def draw_card():
    cards = load_cards()
    now = int(time.time())
    due_cards = [c for c in cards if c.get('next_review', 0) <= now]
    if not due_cards:
        return jsonify({'success': False, 'message': '暂无到期卡片，请稍后再试或添加新卡片！'})
    card = random.choice(due_cards)
    return jsonify({'success': True, 'id': card['id'], 'title': card['title']})

@app.route('/review/<int:card_id>', methods=['POST'])
@login_required
def review_card(card_id):
    data = request.get_json()
    result = data.get('result')  # 'remember' or 'forget'
    cards = load_cards()
    now = int(time.time())
    found = False
    for card in cards:
        if card['id'] == card_id:
            found = True
            if result == 'remember':
                idx = card.get('interval_index', 0)
                idx = min(idx + 1, len(EBBINGHAUS_INTERVALS) - 1)
                card['interval_index'] = idx
                interval_days = EBBINGHAUS_INTERVALS[idx]
                card['next_review'] = now + interval_days * 86400
            else:  # forget
                card['interval_index'] = 0
                card['next_review'] = now + EBBINGHAUS_INTERVALS[0] * 86400
            card['last_review'] = now
            card['review_count'] = card.get('review_count', 0) + 1
            break
    if found:
        save_cards(cards)
        return jsonify({'success': True, 'message': '复习结果已记录'})
    else:
        return jsonify({'success': False, 'message': '未找到卡片'})

@app.route('/reveal/<int:card_id>', methods=['GET'])
@login_required
def reveal_card(card_id):
    cards = load_cards()
    for card in cards:
        if card['id'] == card_id:
            return jsonify({'success': True, 'content': card['content']})
    return jsonify({'success': False, 'message': 'Card not found'})

@app.route('/all_cards', methods=['GET'])
@login_required
def all_cards():
    tag = request.args.get('tag')
    cards = load_cards()
    if tag:
        filtered = [c for c in cards if tag in c.get('tags', [])]
        return jsonify({'success': True, 'cards': filtered})
    tag_map = {}
    for card in cards:
        for t in card.get('tags', []):
            tag_map.setdefault(t, []).append(card)
    return jsonify({'success': True, 'cards': cards, 'by_tag': tag_map})

@app.route('/delete_card/<int:card_id>', methods=['DELETE'])
@login_required
def delete_card(card_id):
    cards = load_cards()
    new_cards = [card for card in cards if card['id'] != card_id]
    for idx, card in enumerate(new_cards):
        card['id'] = idx
    save_cards(new_cards)
    return jsonify({'success': True, 'message': '卡片已删除'})

@app.route('/edit_card/<int:card_id>', methods=['POST'])
@login_required
def edit_card(card_id):
    data = request.get_json()
    new_title = data.get('title')
    new_content = data.get('content')
    new_tags = data.get('tags')
    new_img = data.get('img')
    cards = load_cards()
    found = False
    for card in cards:
        if card['id'] == card_id:
            if new_title:
                card['title'] = new_title
            if new_content:
                card['content'] = new_content
            if new_tags is not None:
                card['tags'] = [t.strip() for t in new_tags if t.strip()]
            if new_img is not None:
                card['img'] = new_img
            found = True
            break
    if found:
        save_cards(cards)
        return jsonify({'success': True, 'message': '卡片已修改'})
    else:
        return jsonify({'success': False, 'message': '未找到卡片'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0') 