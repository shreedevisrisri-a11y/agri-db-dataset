import os
import sqlite3
import cloudinary
import cloudinary.uploader
from flask import Flask, redirect, render_template, request, url_for

app = Flask(__name__)

# Unga Cloudinary Account Credentials
cloudinary.config(
    cloud_name='xczmz3xg',
    api_key='252792712175493',
    api_secret='PbtB4lLkKg_jGq0xaQhCd8LI6fY',
)

DB_NAME = 'dataset.db'


def init_db():
  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  # Database-ல direct Base64-க்கு பதிலா Image Cloud URL-அ சேமிக்கிறோம்
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
  files = request.files.getlist('file')

  if files:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    for file in files:
      if file and file.filename != '':
        filename = file.filename
        # 1. Image-அ Cloudinary Cloud Storage-க்கு Upload பண்றோம்
        upload_result = cloudinary.uploader.upload(file)
        image_url = upload_result['secure_url']

        # 2. Database-ல Kevalam அந்த Image URL-அ மட்டும் சேமிக்கிறோம்
        cursor.execute(
            'INSERT INTO images (filename, image_url) VALUES (?, ?)',
            (filename, image_url),
        )

    conn.commit()
    conn.close()

  return redirect(url_for('index'))


if __name__ == '__main__':
  app.run(debug=True, port=5000)
