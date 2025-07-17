from flask import Flask, render_template, request, redirect, url_for, jsonify, session, send_file
import os
import json
import random
import time
from datetime import datetime, timedelta
import sqlite3

app = Flask(__name__, template_folder='../html')
app.secret_key = 'memory_card_secret_key'
CARDS_FILE = os.path.join(os.path.dirname(__file__), '../cards.json')
USERS_FILE = os.path.join(os.path.dirname(__file__), '../users.json')

# 艾宾浩斯遗忘曲线推荐复习间隔（单位：天）
EBBINGHAUS_INTERVALS = [0, 1, 2, 4, 7, 15, 30, 90, 180, 365]

DB_PATH = os.path.join(os.path.dirname(__file__), '../memory_card.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # 用户表
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            today_draw_count INTEGER DEFAULT 0,
            today_draw_date TEXT
        )
    ''')
    # 卡片表
    c.execute('''
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            tags TEXT,
            img TEXT,
            review_count INTEGER DEFAULT 0,
            next_review INTEGER,
            last_review INTEGER,
            interval_index INTEGER DEFAULT 0,
            owner TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# 启动时自动初始化数据库
init_db()

# 用户相关操作

def get_user_by_username(username):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    return user

def add_user(username, password):
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return False
    conn.close()
    return True

def update_user_draw_count(username, count, date):
    conn = get_db_connection()
    conn.execute('UPDATE users SET today_draw_count = ?, today_draw_date = ? WHERE username = ?', (count, date, username))
    conn.commit()
    conn.close()

def get_all_users():
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users').fetchall()
    conn.close()
    return users

# 卡片相关操作

def add_card(card):
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO cards (title, content, tags, img, review_count, next_review, last_review, interval_index, owner)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        card['title'], card['content'], ','.join(card['tags']), card['img'],
        card.get('review_count', 0), card.get('next_review'), card.get('last_review'),
        card.get('interval_index', 0), card['owner']
    ))
    conn.commit()
    conn.close()

def get_cards_by_owner(owner):
    conn = get_db_connection()
    cards = conn.execute('SELECT * FROM cards WHERE owner = ?', (owner,)).fetchall()
    conn.close()
    return cards

def get_card_by_id(card_id, owner):
    conn = get_db_connection()
    card = conn.execute('SELECT * FROM cards WHERE id = ? AND owner = ?', (card_id, owner)).fetchone()
    conn.close()
    return card

def update_card(card_id, owner, updates):
    conn = get_db_connection()
    fields = ', '.join([f'{k} = ?' for k in updates.keys()])
    values = list(updates.values()) + [card_id, owner]
    conn.execute(f'UPDATE cards SET {fields} WHERE id = ? AND owner = ?', values)
    conn.commit()
    conn.close()

def delete_card(card_id, owner):
    conn = get_db_connection()
    conn.execute('DELETE FROM cards WHERE id = ? AND owner = ?', (card_id, owner))
    conn.commit()
    conn.close()

def load_cards():
    if not os.path.exists(CARDS_FILE):
        return []
    with open(CARDS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_cards(cards):
    with open(CARDS_FILE, 'w', encoding='utf-8') as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)

def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def get_today_date():
    """获取今天的日期字符串，格式：YYYY-MM-DD"""
    return datetime.now().strftime('%Y-%m-%d')

# 替换 get_user_today_draw_count 和 increment_user_draw_count

def get_user_today_draw_count(username):
    user = get_user_by_username(username)
    if user:
        return user['today_draw_count'] or 0
    return 0

def increment_user_draw_count(username):
    user = get_user_by_username(username)
    today = get_today_date()
    if user:
        if user['today_draw_date'] != today:
            update_user_draw_count(username, 1, today)
            return 1
        else:
            new_count = (user['today_draw_count'] or 0) + 1
            update_user_draw_count(username, new_count, today)
            return new_count
    return 0

# 替换注册接口
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'success': False, 'message': '用户名和密码不能为空'})
    if get_user_by_username(username):
        return jsonify({'success': False, 'message': '用户名已存在'})
    if not add_user(username, password):
        return jsonify({'success': False, 'message': '注册失败'})
    session['logged_in'] = True
    session['username'] = username
    return jsonify({'success': True, 'message': '注册成功并已登录'})

# 替换登录接口
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    user = get_user_by_username(username)
    if user and user['password'] == password:
        session['logged_in'] = True
        session['username'] = username
        return jsonify({'success': True, 'message': '登录成功'})
    else:
        return jsonify({'success': False, 'message': '用户名或密码错误'})

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    return jsonify({'success': True, 'message': '已登出'})

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in') or not session.get('username'):
            return jsonify({'success': False, 'message': '请先登录'}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/', methods=['GET'])
def index():
    return send_file('../html/index.html')

# 替换/add接口
@app.route('/add', methods=['POST'])
@login_required
def add_card_route():
    title = request.form.get('title')
    content = request.form.get('content')
    tags = request.form.get('tags', '')
    img = request.form.get('img', '')
    tag_list = [t.strip() for t in tags.split(',') if t.strip()]
    if not title or not content:
        return redirect(url_for('index'))
    now = int(time.time())
    card = {
        'title': title,
        'content': content,
        'tags': tag_list,
        'img': img,
        'review_count': 0,
        'next_review': now,  # 立即可复习
        'last_review': None,
        'interval_index': 0,  # 当前在曲线第几步
        'owner': session['username']
    }
    add_card(card)
    return redirect(url_for('index'))

# 替换/draw接口
@app.route('/draw', methods=['GET'])
@login_required
def draw_card():
    cards = [dict(c) for c in get_cards_by_owner(session['username'])]
    now = int(time.time())
    due_cards = [c for c in cards if (c.get('next_review') or 0) <= now]
    if not due_cards:
        return jsonify({'success': False, 'message': '暂无到期卡片，请稍后再试或添加新卡片！'})
    card = random.choice(due_cards)
    is_manual = request.args.get('manual', 'true').lower() == 'true'
    response_data = {'success': True, 'id': card['id'], 'title': card['title']}
    if is_manual:
        new_count = increment_user_draw_count(session['username'])
        response_data['today_count'] = new_count
    return jsonify(response_data)

# 替换/review/<int:card_id>接口
@app.route('/review/<int:card_id>', methods=['POST'])
@login_required
def review_card(card_id):
    data = request.get_json()
    result = data.get('result')  # 'remember' or 'forget'
    card = get_card_by_id(card_id, session['username'])
    now = int(time.time())
    if card:
        updates = {}
        if result == 'remember':
            idx = card['interval_index']
            idx = min(idx + 1, len(EBBINGHAUS_INTERVALS) - 1)
            updates['interval_index'] = idx
            interval_days = EBBINGHAUS_INTERVALS[idx]
            updates['next_review'] = now + interval_days * 86400
        else:  # forget
            updates['interval_index'] = 0
            updates['next_review'] = now + EBBINGHAUS_INTERVALS[0] * 86400
        updates['last_review'] = now
        updates['review_count'] = (card['review_count'] or 0) + 1
        update_card(card_id, session['username'], updates)
        return jsonify({'success': True, 'message': '复习结果已记录'})
    else:
        return jsonify({'success': False, 'message': '未找到卡片'})

# 替换/reveal/<int:card_id>接口
@app.route('/reveal/<int:card_id>', methods=['GET'])
@login_required
def reveal_card(card_id):
    card = get_card_by_id(card_id, session['username'])
    if card:
        return jsonify({'success': True, 'content': card['content']})
    else:
        return jsonify({'success': False, 'message': 'Card not found'})

# 替换/all_cards接口
@app.route('/all_cards', methods=['GET'])
@login_required
def all_cards():
    cards = [dict(c) for c in get_cards_by_owner(session['username'])]
    # tags 字段转为列表
    for c in cards:
        c['tags'] = c['tags'].split(',') if c['tags'] else []
    return jsonify({'success': True, 'cards': cards})

# 替换/delete_card/<int:card_id>接口
@app.route('/delete_card/<int:card_id>', methods=['DELETE'])
@login_required
def delete_card_route(card_id):
    card = get_card_by_id(card_id, session['username'])
    if card:
        delete_card(card_id, session['username'])
        return jsonify({'success': True, 'message': '卡片已删除'})
    else:
        return jsonify({'success': False, 'message': '未找到卡片'})

# 替换/edit_card/<int:card_id>接口
@app.route('/edit_card/<int:card_id>', methods=['POST'])
@login_required
def edit_card(card_id):
    data = request.get_json()
    updates = {}
    for field in ['title', 'content', 'tags', 'img']:
        if field in data:
            if field == 'tags' and isinstance(data['tags'], list):
                updates['tags'] = ','.join(data['tags'])
            else:
                updates[field] = data[field]
    card = get_card_by_id(card_id, session['username'])
    if card and updates:
        update_card(card_id, session['username'], updates)
        return jsonify({'success': True, 'message': '卡片已修改'})
    else:
        return jsonify({'success': False, 'message': '未找到卡片'})

# 添加 /today_draw_count 路由
@app.route('/today_draw_count', methods=['GET'])
@login_required
def today_draw_count():
    count = get_user_today_draw_count(session['username'])
    return jsonify({'success': True, 'count': count})

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000) 