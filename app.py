import os
import sqlite3
import cloudinary
import cloudinary.uploader
from flask import Flask, jsonify, redirect, render_template, request, url_for

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
  # Single / Small batch chunk upload route for AJAX
  files = request.files.getlist('file')

  if not files:
    return jsonify({'success': False, 'message': 'No files uploaded'}), 400

  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  uploaded_count = 0

  for file in files:
    if file and file.filename != '' and allowed_file(file.filename):
      try:
        filename = os.path.basename(file.filename)
        upload_result = cloudinary.uploader.upload(file)
        image_url = upload_result['secure_url']

        cursor.execute(
            'INSERT INTO images (filename, image_url) VALUES (?, ?)',
            (filename, image_url),
        )
        uploaded_count += 1
      except Exception as e:
        print(f'Upload error: {e}')
        continue

  conn.commit()
  conn.close()

  return jsonify({'success': True, 'count': uploaded_count})


if __name__ == '__main__':
  app.run(debug=True, port=5000)
