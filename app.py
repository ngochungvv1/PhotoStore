from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, abort, jsonify
from werkzeug.utils import secure_filename
from werkzeug.exceptions import HTTPException
from PIL import Image, ImageDraw, ImageFont
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet
from datetime import timedelta 
from flask_session import Session
import secrets
import pyodbc
import os
import random
import string
from utils.image_utils import add_logo_watermark, add_text_watermark, generate_random_text

app = Flask(__name__)
app.secret_key = 'n20dcat043'
UPLOAD_FOLDER = 'static/uploads/'

# At the top of app.py
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=5)
Session(app)

encryption_key = Fernet.generate_key()
cipher_suite = Fernet(encryption_key)

# Kết nối SQL Server
conn = pyodbc.connect("Driver={SQL Server}; Server=LAPTOP-IQ2M6252\SQLEXPRESS; Database=PhotoStore; Trusted_Connection=yes;")

# Configure Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'n20dcat024@student.ptithcm.edu.vn'
app.config['MAIL_PASSWORD'] = 'guzmbcuonlvktqsa'
mail = Mail(app)

def generate_unique_key(length=10):
    """Tạo một key giải mã ngẫu nhiên cho ảnh."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

@app.after_request
def add_security_headers(response):
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'"
    return response

@app.errorhandler(404)
def page_not_found(e):
    return redirect(url_for('index'))

@app.errorhandler(Exception)
def handle_exception(e):
    # Log the error if needed
    app.logger.error(f'Error: {str(e)}')
    return redirect(url_for('index'))

@app.route('/')
def index():
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Images WHERE is_sold = 0")
    images = cursor.fetchall()
    return render_template('index.html', images=images)

def generate_verification_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

# app.py
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            # Handle verification code submission
            if 'verification_code' in request.form:
                verification_code = request.form['verification_code']
                if 'registration_data' not in session:
                    return redirect(url_for('register'))
                
                if verification_code == session['registration_data']['verification_code']:
                    # Insert user into database
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO Users (fullname, email, username, password, role)
                        VALUES (?, ?, ?, ?, 'user')
                    """, (
                        session['registration_data']['fullname'],
                        session['registration_data']['email'],
                        session['registration_data']['username'],
                        session['registration_data']['password']
                    ))
                    conn.commit()
                    
                    # Clear registration data
                    session.pop('registration_data', None)
                    return '', 200
                else:
                    return render_template('verify.html', error='Mã xác thực không đúng')

            # Handle initial registration
            fullname = request.form['fullname']
            email = request.form['email']
            username = request.form['username']
            password = request.form['password']

            # Check existing user
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Users WHERE username = ? OR email = ?", 
                         (username, email))
            if cursor.fetchone():
                return render_template('register.html', 
                                     error='Username hoặc email đã tồn tại')

            # Generate verification code
            code = generate_verification_code()
            
            # Store registration data in session
            session['registration_data'] = {
                'fullname': fullname,
                'email': email,
                'username': username,
                'password': generate_password_hash(password),
                'verification_code': code
            }

            # Send verification email
            try:
                msg = Message('Mã xác thực đăng ký tài khoản',
                            sender=app.config['MAIL_USERNAME'],
                            recipients=[email])
                msg.body = f'Mã xác thực của bạn là: {code}'
                mail.send(msg)
                return render_template('verify.html')
            except Exception as e:
                app.logger.error(f"Failed to send email: {str(e)}")
                return render_template('register.html', 
                                     error='Không thể gửi mã xác thực')

        except Exception as e:
            app.logger.error(f"Registration error: {str(e)}")
            return render_template('register.html', error='Đăng ký thất bại')

    return render_template('register.html')

# app.py - Add new route
@app.route('/check-availability', methods=['POST'])
def check_availability():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        cursor = conn.cursor()
        
        if 'email' in data:
            cursor.execute("SELECT * FROM Users WHERE email = ?", (data['email'],))
            exists = cursor.fetchone() is not None
            return jsonify({'available': not exists})
            
        if 'username' in data:
            cursor.execute("SELECT * FROM Users WHERE username = ?", (data['username'],))
            exists = cursor.fetchone() is not None
            return jsonify({'available': not exists})
        
        return jsonify({'error': 'Invalid request'}), 400
    except Exception as e:
        app.logger.error(f"Availability check error: {str(e)}")
        return jsonify({'error': 'Server error'}), 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor = conn.cursor()
        cursor.execute("SELECT password, role FROM Users WHERE username = ?", (username,))
        result = cursor.fetchone()
        if result and check_password_hash(result[0], password):
            session['username'] = username
            session['role'] = result[1]
            session['logged_in'] = True
            return redirect(url_for('admin_upload') if result[1] == 'admin' else url_for('index'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()  # This clears all session data including logged_in flag
    return redirect(url_for('index'))


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
    print("Session in /library:", session)  # Add this line
    if not session.get('logged_in'):
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
            # Lưu key vào session nếu key nhập đúng
            session[f"{filename}_key"] = input_key

            # Nếu key khớp, cho phép tải phiên bản gốc không có watermark
            return send_from_directory(os.path.dirname(original_filepath), os.path.basename(original_filepath),
                                       as_attachment=True)

    # Nếu key không khớp, chuyển hướng về thư viện
    return redirect(url_for('library'))


if __name__ == '__main__':
    app.run(debug=True)
