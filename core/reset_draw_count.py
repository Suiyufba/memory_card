import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '../memory_card.db')

def reset_draw_count():
    today = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE users SET today_draw_count = 0, today_draw_date = ?", (today,))
    conn.commit()
    conn.close()

if __name__ == '__main__':
    reset_draw_count() 