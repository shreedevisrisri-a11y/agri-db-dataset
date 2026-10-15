import io
import os
import sqlite3
import zipfile
from concurrent.futures import ThreadPoolExecutor
import cloudinary
import cloudinary.uploader
from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
import requests

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
  return (
      '.' in filename
      and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
  )


def init_db():
  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  cursor.execute('''
        CREATE TABLE IF NOT EXISTS dataset_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_name TEXT,
            filename TEXT,
            image_url TEXT
        )
    ''')
  conn.commit()
  conn.close()


init_db()


@app.route('/')
def index():
  search_query = request.args.get('search', '').strip()
  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()

  if search_query:
    cursor.execute(
        '''
            SELECT dataset_name, COUNT(*), MIN(image_url) 
            FROM dataset_images 
            WHERE dataset_name LIKE ? 
            GROUP BY dataset_name 
            ORDER BY id DESC
        ''',
        (f'%{search_query}%',),
    )
  else:
    cursor.execute('''
            SELECT dataset_name, COUNT(*), MIN(image_url) 
            FROM dataset_images 
            GROUP BY dataset_name 
            ORDER BY id DESC
        ''')

  rows = cursor.fetchall()
  conn.close()

  datasets = [
      {'name': row[0], 'count': row[1], 'cover_url': row[2]} for row in rows
  ]
  return render_template('index.html', datasets=datasets, search=search_query)


@app.route('/upload', methods=['POST'])
def upload_file():
  dataset_name = request.form.get('dataset_name', '').strip()
  files = request.files.getlist('file')

  if not dataset_name or not files:
    return jsonify({
        'success': False,
        'message': 'Dataset name and files are required',
    }), 400

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
            'INSERT INTO dataset_images (dataset_name, filename, image_url)'
            ' VALUES (?, ?, ?)',
            (dataset_name, filename, image_url),
        )
        uploaded_count += 1
      except Exception as e:
        print(f'Upload error: {e}')
        continue

  conn.commit()
  conn.close()

  return jsonify({'success': True, 'count': uploaded_count})


@app.route('/download/<dataset_name>')
def download_dataset(dataset_name):
  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  cursor.execute(
      'SELECT filename, image_url FROM dataset_images WHERE dataset_name = ?',
      (dataset_name,),
  )
  rows = cursor.fetchall()
  conn.close()

  if not rows:
    return 'Dataset not found', 404

  # Memory-ல் Zip File உருவாக்கி அனைத்து படங்களையும் டவுன்லோட் செய்து சேர்க்கிறோம்
  zip_buffer = io.BytesIO()

  def fetch_and_zip(row):
    filename, url = row
    try:
      resp = requests.get(url, timeout=10)
      if resp.status_code == 200:
        return (filename, resp.content)
    except Exception as e:
      print(f'Error fetching {url}: {e}')
    return None

  with ThreadPoolExecutor(max_workers=10) as executor:
    results = list(executor.map(fetch_and_zip, rows))

  with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
    for res in results:
      if res:
        filename, content = res
        zip_file.writestr(filename, content)

  zip_buffer.seek(0)
  return send_file(
      zip_buffer,
      mimetype='application/zip',
      as_attachment=True,
      download_name=f'{dataset_name}.zip',
  )


if __name__ == '__main__':
  app.run(debug=True, port=5000)
