from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, abort
from werkzeug.utils import secure_filename
from PIL import Image, ImageDraw, ImageFont
import pyodbc
import os
import random
import string
from utils.image_utils import add_logo_watermark, add_text_watermark, generate_random_text

app = Flask(__name__)
app.secret_key = 'n20dcat043'
UPLOAD_FOLDER = 'static/uploads/'

# Kết nối SQL Server
conn = pyodbc.connect("Driver={SQL Server}; Server=LAPTOP-IQ2M6252\SQLEXPRESS; Database=PhotoStore; Trusted_Connection=yes;")


def generate_unique_key(length=10):
    """Tạo một key giải mã ngẫu nhiên cho ảnh."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


@app.route('/')
def index():
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Images WHERE is_sold = 0")
    images = cursor.fetchall()
    return render_template('index.html', images=images)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor = conn.cursor()
        cursor.execute("SELECT role FROM Users WHERE username = ? AND password = ?", (username, password))
        result = cursor.fetchone()
        if result:
            session['username'] = username
            session['role'] = result[0]
            return redirect(url_for('admin_upload') if result[0] == 'admin' else url_for('index'))
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))


import random
import string
from PIL import Image, ImageDraw, ImageFont
import os

# Hàm tạo chuỗi ngẫu nhiên 6 ký tự
def generate_random_text(length=6):
    letters_and_digits = string.ascii_letters + string.digits
    return ''.join(random.choice(letters_and_digits) for _ in range(length))

@app.route('/admin/upload', methods=['GET', 'POST'])
def admin_upload():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Upload file hình ảnh để bán
        file = request.files['file']
        owner = request.form['owner']

        # Tạo tên file ngẫu nhiên và đảm bảo không trùng lặp
        random_filename = generate_random_text() + ".jpg"
        original_filepath = os.path.join(UPLOAD_FOLDER, random_filename)  # Đường dẫn ảnh gốc
        file.save(original_filepath)

        # Kiểm tra xem có upload logo không
        logo = request.files.get('logo')
        if logo:
            logo_filename = secure_filename(logo.filename)
            logo_filepath = os.path.join(UPLOAD_FOLDER, logo_filename)
            logo.save(logo_filepath)
            # Thêm logo làm watermark
            watermarked_image = add_logo_watermark(original_filepath, logo_filepath)
        else:
            # Thêm tên tác giả làm watermark
            watermarked_image = add_text_watermark(original_filepath, owner)

        # Đặt tên file mới cho ảnh có watermark và lưu nó
        watermarked_filename = random_filename.replace(".jpg", "_watermarked.jpg")
        output_path = os.path.join(UPLOAD_FOLDER, watermarked_filename)
        watermarked_image.save(output_path)

        # Tạo khóa giải mã duy nhất cho ảnh
        decryption_key = generate_unique_key()

        # Lưu thông tin vào database với ảnh đã có watermark
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Images (filename, owner, decryption_key, filepath, original_filepath) VALUES (?, ?, ?, ?, ?)",
                       (watermarked_filename, owner, decryption_key, output_path, original_filepath))
        conn.commit()
        return redirect(url_for('index'))
    return render_template('upload.html')

@app.route('/detail/<int:image_id>')
def detail(image_id):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Images WHERE image_id = ?", (image_id,))
    image = cursor.fetchone()
    return render_template('detail.html', image=image)


@app.route('/purchase/<int:image_id>', methods=['GET', 'POST'])
def purchase(image_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    # Lấy user_id của người dùng hiện tại
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM Users WHERE username = ?", (session['username'],))
    user_id = cursor.fetchone()[0]

    # Kiểm tra nếu người dùng đã mua ảnh này
    cursor.execute("SELECT * FROM Purchases WHERE user_id = ? AND image_id = ?", (user_id, image_id))
    purchase = cursor.fetchone()
    if purchase:
        return redirect(url_for('library'))  # Nếu đã mua, chuyển hướng về thư viện

    # Lấy key giải mã từ bảng Images
    cursor.execute("SELECT decryption_key FROM Images WHERE image_id = ?", (image_id,))
    decryption_key_result = cursor.fetchone()

    # Kiểm tra xem có key giải mã hay không
    if decryption_key_result:
        decryption_key = decryption_key_result[0]

        # Lưu vào bảng Purchases với key giải mã
        cursor.execute("INSERT INTO Purchases (user_id, image_id, decryption_key) VALUES (?, ?, ?)", (user_id, image_id, decryption_key))
        conn.commit()

        # Trả về key giải mã cho người dùng
        return render_template('purchase_key.html', decryption_key=decryption_key)
    else:
        return "Error: No decryption key found for this image."


@app.route('/library')
def library():
    if 'username' not in session:
        return redirect(url_for('login'))

    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM Users WHERE username = ?", (session['username'],))
    user_id = cursor.fetchone()[0]

    cursor.execute("""
        SELECT Images.filename, Purchases.decryption_key 
        FROM Images 
        JOIN Purchases ON Images.image_id = Purchases.image_id 
        WHERE Purchases.user_id = ?
    """, (user_id,))
    purchased_images = cursor.fetchall()

    return render_template('library.html', images=purchased_images)


@app.route('/download/<filename>', methods=['POST'])
def download(filename):
    input_key = request.form['key']
    cursor = conn.cursor()

    # Lấy user_id của người dùng hiện tại
    cursor.execute("SELECT user_id FROM Users WHERE username = ?", (session['username'],))
    user_id = cursor.fetchone()[0]

    # Xác minh key giải mã của người dùng với ảnh cụ thể từ bảng Purchases
    cursor.execute("""
        SELECT Purchases.decryption_key, Images.original_filepath
        FROM Purchases 
        JOIN Images ON Purchases.image_id = Images.image_id 
        WHERE Purchases.user_id = ? AND Images.filename = ?
    """, (user_id, filename))
    
    result = cursor.fetchone()
    if result:
        stored_key, original_filepath = result

        if stored_key == input_key:
            # Nếu key khớp, cho phép tải phiên bản gốc không có watermark
            return send_from_directory(os.path.dirname(original_filepath), os.path.basename(original_filepath), as_attachment=True)
    
    # Nếu key không khớp, chuyển hướng về thư viện
    return redirect(url_for('library'))

if __name__ == '__main__':
    app.run(debug=True)
