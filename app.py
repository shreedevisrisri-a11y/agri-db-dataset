import io
import os
import sqlite3
import zipfile
from concurrent.futures import ThreadPoolExecutor
import cloudinary
import cloudinary.uploader
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
import requests

app = Flask(__name__)
app.secret_key = 'agri_dataset_secret_key_2026'

# Admin Credentials
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin123'

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


# 🌐 PUBLIC SITE ROUTE
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


# 🔐 ADMIN ROUTES & SECURITY
@app.route('/login', methods=['GET', 'POST'])
def login():
  if request.method == 'POST':
    username = request.form.get('username')
    password = request.form.get('password')

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
      session['is_admin'] = True
      return redirect(url_for('admin_dashboard'))
    else:
      flash('Invalid Username or Password!', 'danger')

  return render_template('login.html')


@app.route('/logout')
def logout():
  session.pop('is_admin', None)
  return redirect(url_for('login'))


@app.route('/admin')
def admin_dashboard():
  # Strict Protection: Session illana compulsory Login page-ku poidum
  if not session.get('is_admin'):
    return redirect(url_for('login'))

  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()

  # Get Dataset summary for Admin Cards
  cursor.execute('''
        SELECT dataset_name, COUNT(*), MIN(image_url) 
        FROM dataset_images 
        GROUP BY dataset_name 
        ORDER BY id DESC
    ''')
  rows = cursor.fetchall()

  # Get detailed records for DB inspection table
  cursor.execute(
      'SELECT id, dataset_name, filename, image_url FROM dataset_images ORDER'
      ' BY id DESC'
  )
  db_rows = cursor.fetchall()

  conn.close()

  datasets = [
      {'name': row[0], 'count': row[1], 'cover_url': row[2]} for row in rows
  ]
  db_records = [
      {'id': r[0], 'dataset': r[1], 'filename': r[2], 'url': r[3]}
      for r in db_rows
  ]

  return render_template(
      'admin.html', datasets=datasets, db_records=db_records
  )


@app.route('/upload', methods=['POST'])
def upload_file():
  if not session.get('is_admin'):
    return jsonify({'success': False, 'message': 'Unauthorized'}), 401

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


# 🗑️ DELETE DATASET ROUTE
@app.route('/delete/<dataset_name>', methods=['POST'])
def delete_dataset(dataset_name):
  if not session.get('is_admin'):
    return jsonify({'success': False, 'message': 'Unauthorized'}), 401

  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  cursor.execute(
      'DELETE FROM dataset_images WHERE dataset_name = ?', (dataset_name,)
  )
  conn.commit()
  conn.close()

  return jsonify({'success': True})


if __name__ == '__main__':
  app.run(debug=True, port=5000)
