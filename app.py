import sqlite3
import random
import string
from flask import Flask, request, jsonify, render_template, redirect

app = Flask(__name__, template_folder='.')

# Function to generate a random short code
def generate_short_code(length=6):
    characters = string.ascii_letters + string.digits
    short_code = ''.join(random.choice(characters) for _ in range(length))
    return short_code

# Create a database connection
def get_db_connection():
    conn = sqlite3.connect('urls.db')
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA cache_size = -2000;")
    conn.row_factory = sqlite3.Row
    conn.row_factory = sqlite3.Row
    return conn

# Create the URLs table if it doesn't exist
def create_table():
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
    conn.close()

# Serve the HTML file
@app.route('/')
def index():
    return render_template('index.html')


# Shorten URL endpoint
@app.route('/api/shorten', methods=['POST'])
def shorten_url():
    data = request.get_json()
    original_url = data['url']

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the URL already exists
    cursor.execute('SELECT short_code FROM urls WHERE original_url = ?', (original_url,))
    existing_short_code = cursor.fetchone()

    if existing_short_code:
        short_code = existing_short_code['short_code']
    else:
        # Generate a unique short code
        short_code = generate_short_code()
        while True:
            cursor.execute('SELECT 1 FROM urls WHERE short_code = ?', (short_code,))
            if cursor.fetchone() is None:
                break
            short_code = generate_short_code()

        # Insert the URL and short code into the database
        cursor.execute('INSERT INTO urls (original_url, short_code) VALUES (?, ?)', (original_url, short_code))
        conn.commit()
    conn.close()

    short_url = request.url_root + short_code
    return jsonify({'shortUrl': short_url})

# Redirect to the original URL
@app.route('/<short_code>')
def redirect_to_url(short_code):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT original_url FROM urls WHERE short_code = ?', (short_code,))
    result = cursor.fetchone()
    conn.close()

    if result:
        original_url = result['original_url']
        # Update click count
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE urls SET click_count = click_count + 1 WHERE short_code = ?', (short_code,))
        conn.commit()
        conn.close()
        return redirect(original_url)
    else:
        return 'Short URL not found.'

# Run the Flask app if the script is executed
if __name__ == '__main__':
    create_table()
    app.run(debug=True)

