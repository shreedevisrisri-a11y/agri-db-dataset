import os
import sqlite3
import cloudinary
import cloudinary.uploader
from flask import Flask, redirect, render_template, request, url_for

app = Flask(__name__)

# Cloudinary Details (Unga Account Details-a inga kudunga)
cloudinary.config(
    cloud_name='YOUR_CLOUD_NAME',
    api_key='YOUR_API_KEY',
    api_secret='YOUR_API_SECRET',
)

DB_NAME = 'dataset.db'


def init_db():
  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  # Direct image_data-ku badhula image_url store pannuvom
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
        # Image-a Direct-a Cloudinary-ku Upload panrom
        upload_result = cloudinary.uploader.upload(file)
        image_url = upload_result['secure_url']

        # Database-la Kevalam Image Link (URL)-a mattum Insert panrom
        cursor.execute(
            'INSERT INTO images (filename, image_url) VALUES (?, ?)',
            (filename, image_url),
        )

    conn.commit()
    conn.close()

  return redirect(url_for('index'))


if __name__ == '__main__':
  app.run(debug=True, port=5000)
