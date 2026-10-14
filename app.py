import base64
import sqlite3
import os
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# SQLite Database setup
DB_NAME = 'dataset.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Image content-ஐ Base64 Text-ஆக Database-ல் சேமிக்கும் Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            image_data TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Server ஆரம்பிக்கும் போது Database Table தயாராகும்
init_db()

@app.route('/')
def index():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT filename, image_data FROM images ORDER BY id DESC')
    rows = cursor.fetchall()
    conn.close()
    
    # Database-ல் உள்ள Base64 படங்களை எடுக்கிறது
    images = [{'filename': row[0], 'data': row[1]} for row in rows]
    return render_template('index.html', images=images)

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files.get('file')
    if file and file.filename != '':
        filename = file.filename
        # படத்தை Base64 Text-ஆக மாற்றுகிறது
        encoded_string = base64.b64encode(file.read()).decode('utf-8')
        
        # Local Folder-ல் சேமிக்காமல் நேரடி Database Insert
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO images (filename, image_data) VALUES (?, ?)', (filename, encoded_string))
        conn.commit()
        conn.close()
        
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)