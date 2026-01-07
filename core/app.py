from flask import Flask, render_template, request, redirect, url_for, jsonify, session, send_file
import os
import json
import random
import time
from datetime import datetime, timedelta
import sqlite3
import threading

app = Flask(__name__, template_folder='../html')
app.secret_key = 'memory_card_secret_key'
CARDS_FILE = os.path.join(os.path.dirname(__file__), '../cards.json')
USERS_FILE = os.path.join(os.path.dirname(__file__), '../users.json')

# 艾宾浩斯遗忘曲线推荐复习间隔（单位：天）
EBBINGHAUS_INTERVALS = [0, 1, 2, 4, 7, 15, 30, 90, 180, 365]

DB_PATH = os.path.join(os.path.dirname(__file__), '../memory_card.db')

# 连接池管理
class ConnectionPool:
    def __init__(self, max_connections=10):
        self.max_connections = max_connections
        self.connections = []
        self.lock = threading.Lock()
    
    def get_connection(self):
        with self.lock:
            if self.connections:
                return self.connections.pop()
            else:
                conn = sqlite3.connect(DB_PATH, check_same_thread=False)
                conn.row_factory = sqlite3.Row
                # 启用WAL模式，提高并发读性能
                conn.execute('PRAGMA journal_mode=WAL;')
                # 优化读性能的设置
                conn.execute('PRAGMA synchronous=NORMAL;')
                conn.execute('PRAGMA cache_size=10000;')
                conn.execute('PRAGMA temp_store=memory;')
                return conn
    
    def return_connection(self, conn):
        with self.lock:
            if len(self.connections) < self.max_connections:
                self.connections.append(conn)
            else:
                conn.close()

# 全局连接池
connection_pool = ConnectionPool()

def get_db_connection():
    return connection_pool.get_connection()

def return_db_connection(conn):
    connection_pool.return_connection(conn)

# 缓存装饰器
class SimpleCache:
    def __init__(self, ttl=300):  # 5分钟缓存
        self.cache = {}
        self.ttl = ttl
        self.lock = threading.Lock()
    
    def get(self, key):
        with self.lock:
            if key in self.cache:
                value, timestamp = self.cache[key]
                if time.time() - timestamp < self.ttl:
                    return value
                else:
                    del self.cache[key]
            return None
    
    def set(self, key, value):
        with self.lock:
            self.cache[key] = (value, time.time())
    
    def delete(self, key):
        with self.lock:
            if key in self.cache:
                del self.cache[key]
    
    def clear(self):
        with self.lock:
            self.cache.clear()

# 全局缓存实例
cache = SimpleCache()

def init_db():
    conn = get_db_connection()
    try:
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
    finally:
        return_db_connection(conn)

# 启动时自动初始化数据库
init_db()

# 用户相关操作

def get_user_by_username(username):
    # 先检查缓存
    cache_key = f"user:{username}"
    cached_user = cache.get(cache_key)
    if cached_user is not None:
        return cached_user
    
    conn = get_db_connection()
    try:
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        user_dict = dict(user) if user else None
        # 缓存用户信息
        cache.set(cache_key, user_dict)
        return user_dict
    finally:
        return_db_connection(conn)

def add_user(username, password):
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
        conn.commit()
        # 清除相关缓存
        cache.delete(f"user:{username}")
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        return_db_connection(conn)

def update_user_draw_count(username, count, date):
    conn = get_db_connection()
    try:
        conn.execute('UPDATE users SET today_draw_count = ?, today_draw_date = ? WHERE username = ?', (count, date, username))
        conn.commit()
        # 清除用户缓存
        cache.delete(f"user:{username}")
    finally:
        return_db_connection(conn)

def get_all_users():
    conn = get_db_connection()
    try:
        users = conn.execute('SELECT * FROM users').fetchall()
        return [dict(user) for user in users]
    finally:
        return_db_connection(conn)

# 卡片相关操作

def add_card(card):
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT INTO cards (title, content, tags, img, review_count, next_review, last_review, interval_index, owner)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            card['title'], card['content'], ','.join(card['tags']), card['img'],
            card.get('review_count', 0), card.get('next_review'), card.get('last_review'),
            card.get('interval_index', 0), card['owner']
        ))
        conn.commit()
        # 清除相关缓存
        cache.delete(f"cards:{card['owner']}")
        cache.delete(f"tags:{card['owner']}")
    finally:
        return_db_connection(conn)

def get_cards_by_owner(owner):
    # 先检查缓存
    cache_key = f"cards:{owner}"
    cached_cards = cache.get(cache_key)
    if cached_cards is not None:
        return cached_cards
    
    conn = get_db_connection()
    try:
        cards = conn.execute('SELECT * FROM cards WHERE owner = ? ORDER BY id DESC', (owner,)).fetchall()
        cards_list = [dict(card) for card in cards]
        # 缓存卡片列表
        cache.set(cache_key, cards_list)
        return cards_list
    finally:
        return_db_connection(conn)

def get_card_by_id(card_id, owner):
    # 先检查缓存
    cache_key = f"card:{card_id}:{owner}"
    cached_card = cache.get(cache_key)
    if cached_card is not None:
        return cached_card
    
    conn = get_db_connection()
    try:
        card = conn.execute('SELECT * FROM cards WHERE id = ? AND owner = ?', (card_id, owner)).fetchone()
        card_dict = dict(card) if card else None
        # 缓存单个卡片
        cache.set(cache_key, card_dict)
        return card_dict
    finally:
        return_db_connection(conn)

def update_card(card_id, owner, updates):
    conn = get_db_connection()
    try:
        fields = ', '.join([f'{k} = ?' for k in updates.keys()])
        values = list(updates.values()) + [card_id, owner]
        conn.execute(f'UPDATE cards SET {fields} WHERE id = ? AND owner = ?', values)
        conn.commit()
        # 清除相关缓存
        cache.delete(f"card:{card_id}:{owner}")
        cache.delete(f"cards:{owner}")
        cache.delete(f"tags:{owner}")
    finally:
        return_db_connection(conn)

def delete_card(card_id, owner):
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM cards WHERE id = ? AND owner = ?', (card_id, owner))
        conn.commit()
        # 清除相关缓存
        cache.delete(f"card:{card_id}:{owner}")
        cache.delete(f"cards:{owner}")
        cache.delete(f"tags:{owner}")
        cache.delete(f"due_cards:{owner}")
    finally:
        return_db_connection(conn)

def get_due_cards_by_owner(owner, current_time):
    """获取到期的卡片，专门为抽卡优化"""
    cache_key = f"due_cards:{owner}:{current_time//3600}"  # 按小时缓存
    cached_cards = cache.get(cache_key)
    if cached_cards is not None:
        return cached_cards
    
    conn = get_db_connection()
    try:
        # 使用索引优化的查询
        cards = conn.execute('''
            SELECT * FROM cards 
            WHERE owner = ? AND (next_review IS NULL OR next_review <= ?)
            ORDER BY next_review ASC
        ''', (owner, current_time)).fetchall()
        cards_list = [dict(card) for card in cards]
        # 短时间缓存（1小时）
        cache.set(cache_key, cards_list)
        return cards_list
    finally:
        return_db_connection(conn)

def get_tag_statistics(owner):
    """获取标签统计，读多写少场景的优化"""
    cache_key = f"tags:{owner}"
    cached_tags = cache.get(cache_key)
    if cached_tags is not None:
        return cached_tags
    
    conn = get_db_connection()
    try:
        # 直接在SQL层面进行标签统计，减少应用层处理
        cards = conn.execute('SELECT tags FROM cards WHERE owner = ? AND tags IS NOT NULL AND tags != ""', (owner,)).fetchall()
        tag_count = {}
        for card in cards:
            if card['tags']:
                for tag in card['tags'].split(','):
                    tag = tag.strip()
                    if tag:
                        tag_count[tag] = tag_count.get(tag, 0) + 1
        # 缓存标签统计
        cache.set(cache_key, tag_count)
        return tag_count
    finally:
        return_db_connection(conn)

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

# 记录复习历史

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
    now = int(time.time())
    # 使用优化的查询直接获取到期卡片
    due_cards = get_due_cards_by_owner(session['username'], now)
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
        # 清除到期卡片缓存（get_due_cards_by_owner 按小时分桶）
        cache.delete(f"due_cards:{session['username']}:{now//3600}")
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
    cards = get_cards_by_owner(session['username'])
    # 创建副本避免修改缓存中的原始数据
    cards_copy = []
    for c in cards:
        card_copy = c.copy()
        card_copy['tags'] = card_copy['tags'].split(',') if card_copy['tags'] else []
        cards_copy.append(card_copy)
    return jsonify({'success': True, 'cards': cards_copy})

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

# 新增标签统计API
@app.route('/tag_statistics', methods=['GET'])
@login_required
def tag_statistics():
    tags = get_tag_statistics(session['username'])
    return jsonify({'success': True, 'tags': tags})

# 一键导出所有数据
@app.route('/export_data', methods=['GET'])
@login_required
def export_data():
    conn = get_db_connection()
    try:
        users = [dict(row) for row in conn.execute('SELECT * FROM users')]
        cards = [dict(row) for row in conn.execute('SELECT * FROM cards')]
        return jsonify({'users': users, 'cards': cards})
    finally:
        return_db_connection(conn)

# 一键导入所有数据（JSON格式，覆盖）
@app.route('/import_data', methods=['POST'])
@login_required
def import_data():
    data = request.get_json()
    users = data.get('users', [])
    cards = data.get('cards', [])
    conn = get_db_connection()
    try:
        c = conn.cursor()
        # 使用事务提高导入性能
        c.execute('BEGIN TRANSACTION')
        c.execute('DELETE FROM users')
        c.execute('DELETE FROM cards')
        
        # 批量插入用户
        if users:
            c.executemany('INSERT INTO users (username, password, today_draw_count, today_draw_date) VALUES (?, ?, ?, ?)',
                         [(u['username'], u['password'], u.get('today_draw_count', 0), u.get('today_draw_date')) for u in users])
        
        # 批量插入卡片
        if cards:
            c.executemany('''INSERT INTO cards (title, content, tags, img, review_count, next_review, last_review, interval_index, owner)
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                         [(card['title'], card['content'], card['tags'], card['img'], card.get('review_count', 0),
                           card.get('next_review'), card.get('last_review'), card.get('interval_index', 0), card['owner']) for card in cards])
        
        conn.commit()
        # 清除所有缓存
        cache.clear()
        return jsonify({'success': True, 'message': '数据导入成功'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'导入失败: {str(e)}'})
    finally:
        return_db_connection(conn)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000) 