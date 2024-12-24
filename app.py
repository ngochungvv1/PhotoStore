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
from utils.image_utils import add_logo_watermark, add_text_watermark, generate_random_text, embed_watermark, extract_watermark

app = Flask(__name__)
app.secret_key = 'n20dcat043'
UPLOAD_FOLDER = 'static/uploads/'

# At the top of app.py
# app.config['SESSION_TYPE'] = 'filesystem'
# app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=5)
# Session(app)

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
    cursor.execute("SELECT image_id, filename, owner, is_sold FROM Images WHERE is_sold = 0")
    images = cursor.fetchall()

    # Thay đổi filename thành _display.png nếu có
    updated_images = []
    for image in images:
        image_id, filename, owner, is_sold = image

        # Thay đổi filename từ _watermarked.png thành _display.png
        if '_watermarked.png' in filename:
            display_filename = filename.replace('_watermarked.png', '_display.png')
        else:
            display_filename = filename  # Nếu không phải _watermarked.png, giữ nguyên

        updated_images.append((image_id, display_filename, owner, is_sold))

    return render_template('index.html', images=updated_images)


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
        else:
            return render_template('login.html', error='Tên đăng nhập hoặc mật khẩu không đúng')
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
        # Upload file ảnh và logo
        file = request.files['file']
        logo = request.files.get('logo')  # Logo là tùy chọn
        owner = request.form['owner']
        watermark_type = 'text'  # 'logo' hoặc 'text'

        # Lưu ảnh gốc
        original_filename = secure_filename(file.filename)
        base_name = generate_random_text(10)  # Tạo tên file ngẫu nhiên
        png_filename = f"{base_name}.png"
        png_filepath = os.path.join(UPLOAD_FOLDER, png_filename)

        original_image = Image.open(file).convert("RGB")
        original_image.save(png_filepath, format='PNG')

        # Lưu file logo nếu có
        if logo:
            logo_filename = secure_filename(logo.filename)
            logo_base_name = generate_random_text(10)  # Tạo tên file ngẫu nhiên cho logo
            logo_filepath = os.path.join(UPLOAD_FOLDER, f"{logo_base_name}.png")
            logo_image = Image.open(logo).convert("RGBA")
            logo_image.save(logo_filepath, format='PNG')
        else:
            logo_filepath = None

        # Nhúng watermark ẩn
        if logo_filepath:
            watermark_image = Image.open(logo_filepath).convert("1")
        else:
            watermark_image = Image.new("1", original_image.size, color=0)

        watermarked_image = embed_watermark(original_image, watermark_image)
        watermarked_filename = f"{base_name}_watermarked.png"
        watermarked_filepath = os.path.join(UPLOAD_FOLDER, watermarked_filename)
        watermarked_image.save(watermarked_filepath, format='PNG')

        # Chèn logo hoặc văn bản hiển thị
        if watermark_type == 'text' and owner:
            display_image = add_text_watermark(png_filepath, owner)
        else:
            display_image = add_text_watermark(png_filepath, 'PhotoStore')

        display_filename = f"{base_name}_display.png"
        display_filepath = os.path.join(UPLOAD_FOLDER, display_filename)
        display_image.save(display_filepath, format='PNG')

        # Tạo khóa giải mã
        decryption_key = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

        # Lưu thông tin vào database
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Images (filename, owner, decryption_key, filepath, original_filepath) 
            VALUES (?, ?, ?, ?, ?)
        """, (
            watermarked_filename,
            owner,  
            decryption_key,
            watermarked_filepath,
            png_filepath
        ))
        conn.commit()

        return redirect(url_for('index'))

    return render_template('upload.html')

@app.route('/extract_logo', methods=['GET', 'POST'])
def extract_logo():
    if request.method == 'POST':
        # Upload ảnh đã nhúng watermark
        file = request.files['file']
        uploaded_filepath = os.path.join(UPLOAD_FOLDER, secure_filename(file.filename))
        file.save(uploaded_filepath)

        # Mở ảnh đã nhúng watermark
        watermarked_image = Image.open(uploaded_filepath).convert("RGB")

        # Trích xuất watermark
        extracted_logo = extract_watermark(watermarked_image)

        # Lưu logo đã trích xuất
        extracted_logo_path = uploaded_filepath.replace(".jpg", "_extracted_logo.jpg")
        extracted_logo.save(extracted_logo_path)

        # Gửi ảnh đã trích xuất về người dùng
        return send_from_directory(
            os.path.dirname(extracted_logo_path),
            os.path.basename(extracted_logo_path),
            as_attachment=True
        )

    return render_template('extract_logo.html')

@app.route('/detail/<int:image_id>')
def detail(image_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    cursor = conn.cursor()
    cursor.execute("SELECT image_id, filename, owner FROM Images WHERE image_id = ?", (image_id,))
    image = cursor.fetchone()

    if image:
        image_id, filename, owner = image

        # Thay đổi tên file để hiển thị file _display.png
        if '_watermarked.png' in filename:
            display_filename = filename.replace('_watermarked.png', '_display.png')
        else:
            display_filename = filename

        # Truyền lại tên file _display.png thay vì tên file gốc
        image = (image_id, display_filename, owner)

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
    
    updated_images = []
    for image in purchased_images:
        filename, decryption_key = image

        # Thay đổi filename từ _watermarked.png thành _display.png
        if '_watermarked.png' in filename:
            display_filename = filename.replace('_watermarked.png', '_display.png')
        else:
            display_filename = filename  # Nếu không phải _watermarked.png, giữ nguyên

        updated_images.append((display_filename, decryption_key, filename))

    # return render_template('library.html', images=purchased_images)
    return render_template('library.html', images=updated_images)


@app.route('/download/<filename>', methods=['POST'])
@app.route('/download/<filename>', methods=['POST'])
def download(filename):
    input_key = request.form['key']
    cursor = conn.cursor()

    # Lấy thông tin ảnh từ database dựa trên tên file
    cursor.execute("""
        SELECT Purchases.decryption_key, Images.filepath
        FROM Purchases 
        JOIN Images ON Purchases.image_id = Images.image_id 
        WHERE Purchases.user_id = (SELECT user_id FROM Users WHERE username = ?)
        AND Images.filename = ?
    """, (session['username'], filename))

    result = cursor.fetchone()
    if result:
        stored_key, watermarked_filepath = result

        # Kiểm tra mã giải mã
        if stored_key == input_key:
            # Cho phép tải về file có watermark
            return send_from_directory(
                os.path.dirname(watermarked_filepath),
                os.path.basename(watermarked_filepath),
                as_attachment=True
            )

    # Nếu mã không khớp, chuyển hướng về thư viện với thông báo lỗi
    return redirect(url_for('library'))


@app.route('/edit_image/<int:image_id>', methods=['GET', 'POST'])
def edit_image(image_id):
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    
    cursor = conn.cursor()
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        
        cursor.execute("""
            UPDATE Images 
            SET title = ?, description = ?
            WHERE image_id = ?
        """, (title, description, image_id))
        conn.commit()
        
        return redirect(url_for('detail', image_id=image_id))
    
    # GET request - show edit form
    cursor.execute("SELECT * FROM Images WHERE image_id = ?", (image_id,))
    image = cursor.fetchone()
    if not image:
        return redirect(url_for('index'))
        
    return render_template('edit_image.html', image=image)

@app.route('/delete_image/<int:image_id>')
def delete_image(image_id):
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    
    cursor = conn.cursor()
    
    # Get image path first
    cursor.execute("SELECT file_path FROM Images WHERE image_id = ?", (image_id,))
    image = cursor.fetchone()
    
    if image:
        # Delete file from filesystem
        file_path = os.path.join(app.root_path, 'static/uploads/', image[0])
        if os.path.exists(file_path):
            os.remove(file_path)
            
        # Delete from database
        cursor.execute("DELETE FROM Images WHERE image_id = ?", (image_id,))
        conn.commit()
    
    return redirect(url_for('index'))@app.route('/edit_image/<int:image_id>', methods=['GET', 'POST'])
def edit_image(image_id):
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    
    cursor = conn.cursor()
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        
        cursor.execute("""
            UPDATE Images 
            SET title = ?, description = ?
            WHERE image_id = ?
        """, (title, description, image_id))
        conn.commit()
        
        return redirect(url_for('detail', image_id=image_id))
    
    # GET request - show edit form
    cursor.execute("SELECT * FROM Images WHERE image_id = ?", (image_id,))
    image = cursor.fetchone()
    if not image:
        return redirect(url_for('index'))
        
    return render_template('edit_image.html', image=image)

@app.route('/delete_image/<int:image_id>', endpoint='admin_delete_image')
def delete_image(image_id):
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    
    cursor = conn.cursor()
    
    # Get image path first
    cursor.execute("SELECT file_path FROM Images WHERE image_id = ?", (image_id,))
    image = cursor.fetchone()
    
    if image:
        # Delete file from filesystem
        file_path = os.path.join(app.root_path, 'static/uploads/', image[0])
        if os.path.exists(file_path):
            os.remove(file_path)
            
        # Delete from database
        cursor.execute("DELETE FROM Images WHERE image_id = ?", (image_id,))
        conn.commit()
    
    return redirect(url_for('index'))
# app.py
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'username' not in session:
        return redirect(url_for('login'))

    cursor = conn.cursor()
    
    if request.method == 'POST':
        fullname = request.form['fullname']
        # Update only fullname
        cursor.execute("UPDATE Users SET fullname = ? WHERE username = ?",
                      (fullname, session['username']))
        conn.commit()
        return redirect(url_for('profile'))

    # Fetch user data
    cursor.execute("""
        SELECT fullname, email, username 
        FROM Users 
        WHERE username = ?""", 
        (session['username'],))
    user = cursor.fetchone()
    
    if not user:
        return redirect(url_for('logout'))

    return render_template('profile.html', user=user)

from flask import jsonify, request

@app.route('/search')
def search():
    search_term = request.args.get('term', '').strip()
    cursor = conn.cursor()

    try:
        if search_term:
            cursor.execute("""
                SELECT image_id, filename 
                FROM Images 
                WHERE filename LIKE ?
            """, ('%' + search_term + '%',))
        else:
            cursor.execute("SELECT image_id, filename FROM Images")

        images = cursor.fetchall()
        results = [{'id': img[0], 'filename': img[1]} for img in images]
        return jsonify(results)
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True)
