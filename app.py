import os
import sqlite3
import cloudinary
import cloudinary.uploader
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, redirect, render_template, request, url_for

app = Flask(__name__)

# Cloudinary Credentials
cloudinary.config(
    cloud_name='xczmz3xg',
    api_key='252792712175493',
    api_secret='PbtB4lLkKg_jGq0xaQhCd8LI6fY',
)

DB_NAME = 'dataset.db'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            image_url TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Single Image Upload Helper Function for Threading
def upload_single_file(file_data):
    filename, file_bytes = file_data
    try:
        # Uploading bytes stream directly to Cloudinary in parallel
        upload_result = cloudinary.uploader.upload(file_bytes)
        return (filename, upload_result['secure_url'])
    except Exception as e:
        print(f"Error uploading {filename}: {e}")
        return None

@app.route('/')
def index():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT filename, image_url FROM images ORDER BY id DESC')
    rows = cursor.fetchall()
    conn.close()
    
    images = [{'filename': row[0], 'url': row[1]} for row in rows]
    return render_template('index.html', images=images)

@app.route('/upload', methods=['POST'])
def upload_file():
    files = request.files.getlist('file')
    
    # Valid image files-ஐ மட்டும் பிரிக்கிறோம்
    valid_files = []
    for file in files:
        if file and file.filename != '' and allowed_file(file.filename):
            filename = os.path.basename(file.filename)
            file_bytes = file.read() # Read file into memory bytes for fast parallel processing
            valid_files.append((filename, file_bytes))
            
    if valid_files:
        # 10 Multi-threads பயன்படுத்தி ஒரே நேரத்தில் 10 படங்களை Parallel-ஆ Upload செய்கிறோம்
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(upload_single_file, valid_files))
            
        # Success ஆன Upload-களை மட்டும் ஒரே Batch-ஆக Database-ல் Insert செய்கிறோம்
        successful_uploads = [res for res in results if res is not None]
        
        if successful_uploads:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.executemany(
                'INSERT INTO images (filename, image_url) VALUES (?, ?)',
                successful_uploads
            )
            conn.commit()
            conn.close()
        
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
