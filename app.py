import sqlite3
import random
import string
import os
from flask import Flask, request, jsonify, render_template, redirect

app = Flask(__name__, template_folder='.')

# --- Configuration ---

# Database Setup 
DATABASE = 'urls.db'

# Secret Key (Set a unique secret key for production!)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "your_very_strong_secret_key_here")

# --- Database Functions ---

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA cache_size = -2000;")
    conn.row_factory = sqlite3.Row
    return conn

def create_table():
    with app.app_context():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_url TEXT NOT NULL,
                short_code TEXT NOT NULL UNIQUE,
                click_count INTEGER DEFAULT 0
            )
        ''')
        conn.commit()

# --- URL Shortening Logic ---

def generate_short_code(length=6):
    characters = string.ascii_letters + string.digits
    short_code = ''.join(random.choice(characters) for _ in range(length))
    return short_code

def shorten_url(original_url):
    with app.app_context():
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT short_code FROM urls WHERE original_url = ?', (original_url,))
        existing_short_code = cursor.fetchone()

        if existing_short_code:
            short_code = existing_short_code['short_code']
        else:
            short_code = generate_short_code()
            while True:
                cursor.execute('SELECT 1 FROM urls WHERE short_code = ?', (short_code,))
                if cursor.fetchone() is None:
                    break
                short_code = generate_short_code()

            cursor.execute('INSERT INTO urls (original_url, short_code) VALUES (?, ?)', 
                           (original_url, short_code))
            conn.commit()

        short_url = request.url_root + short_code
        return short_url

# --- Flask Routes ---

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        original_url = request.form['url']
        short_url = shorten_url(original_url)
        return render_template('index.html', short_url=short_url)
    else:
        return render_template('index.html')

@app.route('/api/shorten', methods=['POST'])
def api_shorten_url():
    data = request.get_json()
    original_url = data['url']
    short_url = shorten_url(original_url)
    return jsonify({'shortUrl': short_url})

@app.route('/<short_code>')
def redirect_to_url(short_code):
    with app.app_context():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT original_url FROM urls WHERE short_code = ?', (short_code,))
        result = cursor.fetchone()

        if result:
            original_url = result['original_url']
            cursor.execute('UPDATE urls SET click_count = click_count + 1 WHERE short_code = ?', (short_code,))
            conn.commit()
            return redirect(original_url)
        else:
            return 'Short URL not found.'

# --- Initialize Database and Run ---

create_table()

if __name__ == '__main__':
    # Set debug mode using environment variable (Important!)
    app.debug = os.environ.get("FLASK_DEBUG") == "1"  
    app.run() 
