import os
import hashlib
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, session, redirect, url_for, flash, jsonify
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, template_folder='template', static_folder='static')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'kos-super-secret-key')
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ─── Database Helpers ───────────────────────────────────────────
def get_db_connection():
    conn = psycopg.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        port=os.environ.get('DB_PORT', '5432'),
        dbname=os.environ.get('DB_NAME', 'gimina_kost'),
        user=os.environ.get('DB_USER', 'postgres'),
        password=os.environ.get('DB_PASSWORD', 'postgres'),
        row_factory=dict_row
    )
    return conn

# ─── Auth Decorators ───────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash('Silakan login terlebih dahulu.', 'warning')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return wrapper

def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('admin_login'))
            user_role = session.get('role', '').upper()
            # Owner ALWAYS has access to everything
            if user_role not in [r.upper() for r in allowed_roles] and user_role != 'OWNER':
                flash('Akses ditolak — Anda tidak memiliki izin.', 'danger')
                return redirect(url_for('admin_dashboard'))
            return f(*args, **kwargs)
        return wrapper
    return decorator

# ─── PUBLIC ROUTES (Portal Penghuni) ──────────────────────────────────
@app.route('/')
def public_home():
    return render_template('portal/index.html')

@app.route('/lokasi/<int:lokasi_id>')
def detail_kos(lokasi_id):
    # Base info based on location ID
    if lokasi_id == 1:
        kos_name = "Gimina Kost Jatinangor"
        address = "Jatinangor, Sumedang"
        price = "Rp 1.500.000"
        facilities = ["Kasur Springbed", "Lemari Pakaian", "Kamar Mandi Dalam", "WiFi Gratis", "Dapur Bersama", "Area Parkir"]
        description = "Gimina Kost Jatinangor merupakan pilihan tepat bagi mahasiswa maupun pekerja yang mencari hunian nyaman dan strategis di area pendidikan Jatinangor."
        image_file = "jatinangor.jpg"
    elif lokasi_id == 2:
        kos_name = "Gimina Kost Gunung Batu"
        address = "Gunung Batu, Bandung"
        price = "Rp 1.500.000"
        facilities = ["Kasur Springbed", "Lemari Pakaian", "Kamar Mandi Dalam", "WiFi Gratis", "Ruang Santai", "Akses 24 Jam"]
        description = "Berlokasi di lingkungan asri Gunung Batu, kos ini sangat cocok untuk karyawan dan profesional muda yang menginginkan ketenangan setelah seharian bekerja."
        image_file = "gunungbatu.jpg"
    else:
        flash("Lokasi kos tidak ditemukan.", "danger")
        return redirect(url_for('public_home'))
        
    conn = get_db_connection()
    cursor = conn.cursor(row_factory=dict_row)
    cursor.execute("SELECT * FROM kamar WHERE location_id = %s ORDER BY room_number ASC", (lokasi_id,))
    rooms = cursor.fetchall()
    cursor.close()
    conn.close()
        
    return render_template('portal/detail_kos.html', 
                           lokasi_id=lokasi_id, 
                           kos_name=kos_name, 
                           address=address, 
                           price=price, 
                           facilities=facilities, 
                           description=description,
                           rooms=rooms,
                           image_file=image_file)

@app.route('/daftar_tunggu', methods=['POST'])
def submit_daftar_tunggu():
    lokasi_id = request.form.get('lokasi_id')
    tipe_kamar = request.form.get('tipe_kamar')
    nama_lengkap = request.form.get('nama_lengkap')
    no_hp = request.form.get('no_hp')
    status_tanggal = request.form.get('status_tanggal')
    tanggal_masuk = request.form.get('tanggal_masuk') if status_tanggal == 'Iya, sudah ada tanggal pasti' else None

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO daftar_tunggu (lokasi_id, tipe_kamar, nama_lengkap, no_hp, status_tanggal, tanggal_masuk)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (lokasi_id, tipe_kamar, nama_lengkap, no_hp, status_tanggal, tanggal_masuk))
        conn.commit()
        flash('Berhasil masuk daftar tunggu! Tim kami akan segera menghubungi Anda melalui WhatsApp.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Terjadi kesalahan: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()
        
    return redirect(url_for('detail_kos', lokasi_id=lokasi_id))

@app.route('/login-penghuni', methods=['GET', 'POST'])
def login_penghuni():
    if request.method == 'POST':
        email_or_phone = request.form.get('email_or_phone')
        password = request.form.get('password')
        
        conn = get_db_connection()
        cursor = conn.cursor(row_factory=dict_row)
        # Check by email or phone
        cursor.execute("SELECT * FROM penghuni WHERE email = %s OR phone = %s", (email_or_phone, email_or_phone))
        penghuni = cursor.fetchone()
        cursor.close()
        conn.close()

        # For demonstration: If password_hash exists, check it. Otherwise just allow if match found
        if penghuni:
            if penghuni['password_hash']:
                from werkzeug.security import check_password_hash
                if check_password_hash(penghuni['password_hash'], password):
                    session['penghuni_id'] = penghuni['id']
                    session['penghuni_name'] = penghuni['full_name']
                    flash('Berhasil masuk ke Portal Penghuni.', 'success')
                    next_url = request.args.get('next')
                    return redirect(next_url or url_for('penghuni_dashboard'))
                else:
                    flash('Password salah.', 'danger')
            else:
                # Fallback if password is not set but tenant exists (for existing data)
                if password == 'Gimina2026': # Default temp password
                    session['penghuni_id'] = penghuni['id']
                    session['penghuni_name'] = penghuni['full_name']
                    flash('Berhasil masuk ke Portal Penghuni.', 'success')
                    next_url = request.args.get('next')
                    return redirect(next_url or url_for('penghuni_dashboard'))
                else:
                    flash('Gunakan password default Gimina2026 atau hubungi admin.', 'danger')
        else:
            flash('Akun tidak ditemukan. Pastikan Anda sudah resmi terdaftar oleh Admin.', 'danger')
            
    return render_template('portal/login_penghuni.html')

@app.route('/logout-penghuni')
def logout_penghuni():
    session.pop('penghuni_id', None)
    session.pop('penghuni_name', None)
    flash('Anda telah keluar dari Portal Penghuni.', 'success')
    return redirect(url_for('public_home'))

@app.route('/penghuni/dashboard')
def penghuni_dashboard():
    if 'penghuni_id' not in session:
        flash('Silakan masuk terlebih dahulu.', 'danger')
        return redirect(url_for('login_penghuni'))
        
    tenant_id = session['penghuni_id']
    conn = get_db_connection()
    cursor = conn.cursor(row_factory=dict_row)
    
    # Check if user has any rental contracts
    cursor.execute('''
        SELECT k.*, r.room_number, l.nama_lokasi 
        FROM kontrak_sewa k
        JOIN kamar r ON k.room_id = r.id
        JOIN lokasi_kos l ON r.location_id = l.id
        WHERE k.tenant_id = %s
        ORDER BY k.id DESC
    ''', (tenant_id,))
    rentals = cursor.fetchall()
    cursor.close()
    conn.close()
    
    has_room = len(rentals) > 0
        
    return render_template('portal/dashboard_penghuni.html', has_room=has_room, rentals=rentals)

@app.route('/pendaftaran', methods=['GET', 'POST'])
def pendaftaran():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        
        from werkzeug.security import generate_password_hash
        hashed_password = generate_password_hash(password)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO penghuni (full_name, email, phone, password_hash, status) 
                VALUES (%s, %s, %s, %s, 'PENDING') RETURNING id
            ''', (full_name, email, phone, hashed_password))
            
            conn.commit()
            flash('Akun berhasil dibuat. Silakan masuk (login) untuk memilih kamar.', 'success')
            next_url = request.args.get('next')
            if next_url:
                return redirect(url_for('login_penghuni', next=next_url))
            return redirect(url_for('login_penghuni'))
        except Exception as e:
            conn.rollback()
            error_msg = str(e)
            if 'duplicate key' in error_msg and 'email' in error_msg:
                flash('Pendaftaran gagal: Email tersebut sudah terdaftar.', 'danger')
            elif 'duplicate key' in error_msg and 'phone' in error_msg:
                flash('Pendaftaran gagal: Nomor HP tersebut sudah terdaftar.', 'danger')
            else:
                flash(f'Terjadi kesalahan saat mendaftar: {error_msg}', 'danger')
        finally:
            cursor.close()
            conn.close()
            
    return render_template('portal/pendaftaran.html')
            
@app.route('/ajukan-sewa/<int:room_id>', methods=['GET', 'POST'])
def ajukan_sewa(room_id):
    if 'penghuni_id' not in session:
        flash('Silakan masuk (login) ke Portal Penghuni terlebih dahulu untuk mengajukan sewa kamar.', 'danger')
        return redirect(url_for('login_penghuni', next=request.path))
        
    tenant_id = session['penghuni_id']
    conn = get_db_connection()
    cursor = conn.cursor(row_factory=dict_row)
    
    # Check room
    cursor.execute("SELECT k.*, l.nama_lokasi FROM kamar k JOIN lokasi_kos l ON k.location_id = l.id WHERE k.id = %s", (room_id,))
    room = cursor.fetchone()
    
    if not room or room['status'] != 'AVAILABLE':
        cursor.close()
        conn.close()
        flash('Kamar tidak tersedia.', 'danger')
        return redirect(url_for('public_home'))
        
    if request.method == 'POST':
        nik = request.form.get('nik')
        origin_address = request.form.get('origin_address')
        occupation = request.form.get('occupation')
        
        try:
            # Update tenant details
            cursor.execute('''
                UPDATE penghuni 
                SET nik = %s, origin_address = %s, occupation = %s
                WHERE id = %s
            ''', (nik, origin_address, occupation, tenant_id))
            
            # Handle KTP Upload
            if 'ktp_image' in request.files:
                file = request.files['ktp_image']
                if file.filename != '':
                    filename = f"ktp_{tenant_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    
                    cursor.execute('''
                        INSERT INTO dokumen_penghuni (tenant_id, document_type, document_url)
                        VALUES (%s, 'KTP', %s)
                    ''', (tenant_id, filename))
            
            # Book room (Create pending contract or just mark as requested - for now let's just use daftar_tunggu concept but for specific room, or create inactive contract)
            cursor.execute('''
                INSERT INTO kontrak_sewa (tenant_id, room_id, start_date, monthly_rate, status)
                VALUES (%s, %s, CURRENT_DATE, %s, 'PENDING')
            ''', (tenant_id, room_id, room['monthly_rate']))
            
            # Lock room temporarily
            cursor.execute("UPDATE kamar SET status = 'RESERVED' WHERE id = %s", (room_id,))
            
            conn.commit()
            flash('Pengajuan sewa berhasil. Silakan selesaikan pembayaran DP/Bulan pertama melalui menu Pembayaran.', 'success')
            return redirect(url_for('penghuni_dashboard'))
        except Exception as e:
            conn.rollback()
            error_msg = str(e)
            if 'duplicate key' in error_msg and 'nik' in error_msg:
                flash('Pengajuan gagal: NIK tersebut sudah terdaftar di sistem.', 'danger')
            else:
                flash(f'Terjadi kesalahan: {error_msg}', 'danger')
        finally:
            cursor.close()
            conn.close()
            
    # GET request
    cursor.close()
    conn.close()
    return render_template('portal/ajukan_sewa.html', room=room)

@app.route('/keluhan', methods=['GET', 'POST'])
def public_keluhan():
    if 'penghuni_id' not in session:
        flash('Silakan masuk (login) ke Portal Penghuni terlebih dahulu untuk melapor keluhan.', 'danger')
        return redirect(url_for('login_penghuni'))
        
    tenant_id = session['penghuni_id']

    if request.method == 'POST':
        category = request.form.get('category')
        title = request.form.get('title')
        description = request.form.get('description')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT room_id FROM kontrak_sewa 
                WHERE tenant_id = %s AND status = 'ACTIVE'
            ''', (tenant_id,))
            contract = cursor.fetchone()
            if not contract:
                flash('Anda tidak memiliki kamar aktif.', 'danger')
                return redirect(url_for('public_keluhan'))
            
            cursor.execute('''
                INSERT INTO keluhan (tenant_id, room_id, category, title, description) 
                VALUES (%s, %s, %s, %s, %s)
            ''', (tenant_id, contract['room_id'], category, title, description))
            conn.commit()
            flash('Keluhan berhasil dikirim.', 'success')
            return redirect(url_for('penghuni_dashboard'))
        except Exception as e:
            conn.rollback()
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()
            
    return render_template('portal/keluhan.html')

@app.route('/pembayaran', methods=['GET', 'POST'])
def public_pembayaran():
    if 'penghuni_id' not in session:
        flash('Silakan masuk (login) ke Portal Penghuni terlebih dahulu untuk mengirim pembayaran.', 'danger')
        return redirect(url_for('login_penghuni'))
        
    tenant_id = session['penghuni_id']

    if request.method == 'POST':
        method = request.form.get('method')
        
        proof_url = None
        if 'proof' in request.files:
            file = request.files['proof']
            if file.filename != '':
                filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                proof_url = filename
        
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Find active contract
            cursor.execute("SELECT id FROM kontrak_sewa WHERE tenant_id = %s AND status = 'ACTIVE'", (tenant_id,))
            contract = cursor.fetchone()
            if not contract:
                flash('Tidak ada kontrak sewa aktif untuk penghuni ini.', 'danger')
                return redirect(url_for('public_pembayaran'))
                
            # Find UNPAID tagihan
            cursor.execute("SELECT id, amount FROM tagihan WHERE contract_id = %s AND status = 'UNPAID' ORDER BY due_date ASC LIMIT 1", (contract['id'],))
            invoice = cursor.fetchone()
            if not invoice:
                flash('Tidak ada tagihan yang belum dibayar (UNPAID) saat ini.', 'success')
                return redirect(url_for('public_pembayaran'))
                
            # Insert pembayaran
            cursor.execute('''
                INSERT INTO pembayaran (invoice_id, amount, method, proof_url, status) 
                VALUES (%s, %s, %s, %s, 'PENDING')
            ''', (invoice['id'], invoice['amount'], method, proof_url))
            
            # Update tagihan status to PENDING
            cursor.execute("UPDATE tagihan SET status = 'PENDING' WHERE id = %s", (invoice['id'],))
            
            conn.commit()
            flash('Bukti pembayaran berhasil dikirim. Menunggu verifikasi admin.', 'success')
            return redirect(url_for('penghuni_dashboard'))
        except Exception as e:
            conn.rollback()
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()
            
    return render_template('portal/pembayaran.html')

# ─── ADMIN ROUTES (Dashboard Internal) ──────────────────────────────────
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if 'user_id' in session:
        return redirect(url_for('admin_dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.*, r.name as role_name 
            FROM users u JOIN roles r ON u.role_id = r.id 
            WHERE u.email = %s AND u.status = 'ACTIVE'
        ''', (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user:
            hashed_pwd = hashlib.md5(password.encode()).hexdigest()
            if user['password_hash'] == hashed_pwd or user['password_hash'] == password:
                session['user_id'] = user['id']
                session['name'] = user['name']
                session['role'] = user['role_name']
                return redirect(url_for('admin_dashboard'))
                
        flash('Email atau password salah!', 'danger')
        
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as total FROM penghuni WHERE status = 'ACTIVE'")
    total_penghuni = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as total FROM kamar")
    total_kamar = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as total FROM kamar WHERE status = 'OCCUPIED'")
    kamar_terisi = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as total FROM keluhan WHERE status = 'NEW'")
    keluhan_baru = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as total FROM pembayaran WHERE status = 'PENDING'")
    pembayaran_pending = cursor.fetchone()['total']
    
    cursor.execute('''
        SELECT 'Pendaftaran' as tipe, full_name as deskripsi, created_at as waktu, 'text-primary' as color_class, 'fa-user-plus' as icon
        FROM penghuni 
        ORDER BY created_at DESC LIMIT 5
    ''')
    act_penghuni = cursor.fetchall()
    
    cursor.execute('''
        SELECT 'Disetujui' as tipe, full_name as deskripsi, verified_at as waktu, 'text-success' as color_class, 'fa-check-circle' as icon
        FROM penghuni 
        WHERE verified_at IS NOT NULL
        ORDER BY verified_at DESC LIMIT 5
    ''')
    act_approve = cursor.fetchall()
    
    cursor.execute('''
        SELECT 'Keluhan/Perbaikan' as tipe, title as deskripsi, created_at as waktu, 'text-warning' as color_class, 'fa-exclamation-triangle' as icon
        FROM keluhan
        ORDER BY created_at DESC LIMIT 5
    ''')
    act_keluhan = cursor.fetchall()
    
    aktivitas = act_penghuni + act_approve + act_keluhan
    aktivitas.sort(key=lambda x: x['waktu'], reverse=True)
    aktivitas = aktivitas[:5]
    
    cursor.close()
    conn.close()
    
    return render_template('admin/dashboard.html', 
                           total_penghuni=total_penghuni, 
                           kamar_terisi=kamar_terisi,
                           kamar_kosong=total_kamar - kamar_terisi,
                           keluhan_baru=keluhan_baru,
                           pembayaran_pending=pembayaran_pending,
                           aktivitas=aktivitas)

@app.route('/admin/penghuni')
@login_required
def admin_penghuni():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.*, d.document_url as ktp_url
        FROM penghuni p
        LEFT JOIN dokumen_penghuni d ON p.id = d.tenant_id AND d.document_type = 'KTP'
        ORDER BY p.id DESC
    ''')
    penghuni = cursor.fetchall()
    
    # Ambil daftar kamar yang AVAILABLE untuk form approval
    cursor.execute('''
        SELECT k.id, k.room_number, k.monthly_rate, l.nama_lokasi 
        FROM kamar k
        JOIN lokasi_kos l ON k.location_id = l.id
        WHERE k.status = 'AVAILABLE'
        ORDER BY l.id ASC, k.room_number ASC
    ''')
    kamar_tersedia = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return render_template('admin/penghuni.html', penghuni=penghuni, kamar_tersedia=kamar_tersedia)

@app.route('/admin/penghuni/approve/<int:id>', methods=['POST'])
@login_required
def admin_penghuni_approve(id):
    room_id = request.form.get('room_id')
    start_date = request.form.get('start_date')
    due_day = request.form.get('due_day', 1)
    payment_cycle = request.form.get('payment_cycle', type=int, default=1)
    
    if not room_id or not start_date:
        flash('Gagal: Anda harus memilih kamar dan mengisi tanggal mulai sewa.', 'danger')
        return redirect(url_for('admin_penghuni'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Get room rate
        cursor.execute("SELECT monthly_rate FROM kamar WHERE id = %s", (room_id,))
        room = cursor.fetchone()
        
        # 1. Update status penghuni
        cursor.execute("UPDATE penghuni SET status = 'ACTIVE', verified_at = CURRENT_TIMESTAMP WHERE id = %s", (id,))
        
        # 2. Buat kontrak sewa
        cursor.execute('''
            INSERT INTO kontrak_sewa (tenant_id, room_id, start_date, monthly_rate, due_day, payment_cycle, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'ACTIVE') RETURNING id
        ''', (id, room_id, start_date, room['monthly_rate'], due_day, payment_cycle))
        contract_id = cursor.fetchone()['id']
        
        # 2b. Buat tagihan pertama (Sesuai Siklus Pembayaran)
        from datetime import datetime
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        period_str = start_dt.strftime('%Y-%m')
        
        amount_to_bill = room['monthly_rate'] * payment_cycle
        
        if payment_cycle == 1:
            period_label = f"1 Bln ({period_str})"
        else:
            period_label = f"{payment_cycle} Bln ({period_str})"
            
        cursor.execute('''
            INSERT INTO tagihan (contract_id, period, amount, due_date, status)
            VALUES (%s, %s, %s, %s, 'UNPAID')
        ''', (contract_id, period_label, amount_to_bill, start_date))
        
        # 3. Update status kamar
        cursor.execute("UPDATE kamar SET status = 'OCCUPIED' WHERE id = %s", (room_id,))
        
        conn.commit()
        flash('Penghuni berhasil di-approve dan kamar telah dialokasikan.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Gagal melakukan approval: {e}', 'danger')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('admin_penghuni'))

@app.route('/admin/penghuni/checkout/<int:id>', methods=['POST'])
@login_required
def admin_penghuni_checkout(id):
    notes = request.form.get('notes')
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 1. Cari kontrak aktif
        cursor.execute("SELECT id, room_id, start_date FROM kontrak_sewa WHERE tenant_id = %s AND status = 'ACTIVE'", (id,))
        contract = cursor.fetchone()
        
        if contract:
            # 2. Update kontrak
            cursor.execute("UPDATE kontrak_sewa SET status = 'ENDED', end_date = CURRENT_DATE WHERE id = %s", (contract['id'],))
            
            # 3. Update kamar jadi available
            cursor.execute("UPDATE kamar SET status = 'AVAILABLE' WHERE id = %s", (contract['room_id'],))
            
            # 4. Catat di checkin_checkout
            cursor.execute('''
                INSERT INTO checkin_checkout (tenant_id, room_id, checkin_date, checkout_date, notes) 
                VALUES (%s, %s, %s, CURRENT_DATE, %s)
            ''', (id, contract['room_id'], contract['start_date'], notes))
            
        # 5. Update status penghuni
        cursor.execute("UPDATE penghuni SET status = 'INACTIVE' WHERE id = %s", (id,))
        
        conn.commit()
        flash('Penghuni berhasil di-checkout. Kamar kembali tersedia.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Gagal melakukan checkout: {e}', 'danger')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('admin_penghuni'))

# --- KAMAR ROUTES ---
@app.route('/admin/kamar/jatinangor')
@login_required
def admin_kamar_jatinangor():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT k.*, l.nama_lokasi 
        FROM kamar k JOIN lokasi_kos l ON k.location_id = l.id 
        WHERE l.id = 1 ORDER BY k.room_number ASC
    ''')
    kamar = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin/kamar.html', kamar=kamar, lokasi_id=1, nama_lokasi='Jatinangor')

@app.route('/admin/kamar/gunungbatu')
@login_required
def admin_kamar_gunungbatu():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT k.*, l.nama_lokasi 
        FROM kamar k JOIN lokasi_kos l ON k.location_id = l.id 
        WHERE l.id = 2 ORDER BY k.room_number ASC
    ''')
    kamar = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin/kamar.html', kamar=kamar, lokasi_id=2, nama_lokasi='Gunung Batu')

@app.route('/admin/kamar/add', methods=['POST'])
@login_required
def admin_kamar_add():
    location_id = request.form.get('location_id')
    room_number = request.form.get('room_number')
    monthly_rate = request.form.get('monthly_rate')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO kamar (location_id, room_number, monthly_rate) VALUES (%s, %s, %s)",
                       (location_id, room_number, monthly_rate))
        conn.commit()
        flash('Kamar berhasil ditambahkan.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Gagal menambahkan kamar: {e}', 'danger')
    finally:
        cursor.close()
        conn.close()
    
    if str(location_id) == '1':
        return redirect(url_for('admin_kamar_jatinangor'))
    else:
        return redirect(url_for('admin_kamar_gunungbatu'))

@app.route('/admin/kamar/delete/<int:id>')
@login_required
def admin_kamar_delete(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM kamar WHERE id = %s", (id,))
        conn.commit()
        flash('Kamar berhasil dihapus.', 'success')
    except Exception as e:
        conn.rollback()
        flash('Tidak bisa menghapus kamar karena masih memiliki data terkait (kontrak/penghuni).', 'danger')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('admin_kamar'))

# --- INVENTARIS ROUTES ---
@app.route('/admin/inventaris')
@login_required
def admin_inventaris():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT i.*, l.nama_lokasi FROM inventaris i 
        JOIN lokasi_kos l ON i.location_id = l.id 
        WHERE l.id = 1 ORDER BY i.nama_barang ASC
    ''')
    inv_jatinangor = cursor.fetchall()
    
    cursor.execute('''
        SELECT i.*, l.nama_lokasi FROM inventaris i 
        JOIN lokasi_kos l ON i.location_id = l.id 
        WHERE l.id = 2 ORDER BY i.nama_barang ASC
    ''')
    inv_gunungbatu = cursor.fetchall()
    
    cursor.execute("SELECT * FROM lokasi_kos ORDER BY id ASC")
    lokasi = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return render_template('admin/inventaris.html', inv_jatinangor=inv_jatinangor, inv_gunungbatu=inv_gunungbatu, lokasi=lokasi)

@app.route('/admin/inventaris/add', methods=['POST'])
@login_required
def admin_inventaris_add():
    location_id = request.form.get('location_id')
    nama_barang = request.form.get('nama_barang')
    jumlah = request.form.get('jumlah')
    kondisi = request.form.get('kondisi')
    keterangan = request.form.get('keterangan')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO inventaris (location_id, nama_barang, jumlah, kondisi, keterangan) 
            VALUES (%s, %s, %s, %s, %s)
        ''', (location_id, nama_barang, jumlah, kondisi, keterangan))
        conn.commit()
        flash('Barang berhasil ditambahkan ke inventaris.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Gagal menambahkan barang: {e}', 'danger')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('admin_inventaris'))

@app.route('/admin/inventaris/delete/<int:id>')
@login_required
def admin_inventaris_delete(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM inventaris WHERE id = %s", (id,))
        conn.commit()
        flash('Barang berhasil dihapus.', 'success')
    except Exception as e:
        conn.rollback()
        flash('Gagal menghapus barang.', 'danger')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('admin_inventaris'))

@app.route('/admin/pembayaran')
@login_required
def admin_pembayaran():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.*, t.period, k.room_number, ph.full_name as tenant_name 
        FROM pembayaran p
        JOIN tagihan t ON p.invoice_id = t.id
        JOIN kontrak_sewa ks ON t.contract_id = ks.id
        JOIN kamar k ON ks.room_id = k.id
        JOIN penghuni ph ON ks.tenant_id = ph.id
        ORDER BY p.id DESC
    ''')
    pembayaran = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin/pembayaran.html', pembayaran=pembayaran)

@app.route('/admin/pembayaran/verify/<int:id>', methods=['POST'])
@login_required
def admin_pembayaran_verify(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT invoice_id FROM pembayaran WHERE id = %s", (id,))
        pemb = cursor.fetchone()
        
        cursor.execute("UPDATE pembayaran SET status = 'PAID' WHERE id = %s", (id,))
        cursor.execute("UPDATE tagihan SET status = 'PAID' WHERE id = %s", (pemb['invoice_id'],))
        
        conn.commit()
        flash('Pembayaran berhasil diverifikasi.', 'success')
    except Exception as e:
        conn.rollback()
        flash('Gagal verifikasi pembayaran.', 'danger')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('admin_pembayaran'))

@app.route('/admin/tagihan')
@login_required
def admin_tagihan():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT t.*, ph.full_name as tenant_name, k.room_number, l.nama_lokasi
        FROM tagihan t
        JOIN kontrak_sewa ks ON t.contract_id = ks.id
        JOIN kamar k ON ks.room_id = k.id
        JOIN lokasi_kos l ON k.location_id = l.id
        JOIN penghuni ph ON ks.tenant_id = ph.id
        ORDER BY t.id DESC
    ''')
    tagihan = cursor.fetchall()
    
    cursor.execute('''
        SELECT ks.id, ph.full_name, k.room_number 
        FROM kontrak_sewa ks
        JOIN penghuni ph ON ks.tenant_id = ph.id
        JOIN kamar k ON ks.room_id = k.id
        WHERE ks.status = 'ACTIVE'
    ''')
    kontrak_aktif = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return render_template('admin/tagihan.html', tagihan=tagihan, kontrak=kontrak_aktif)

@app.route('/admin/tagihan/add', methods=['POST'])
@login_required
def admin_tagihan_add():
    contract_id = request.form.get('contract_id')
    period = request.form.get('period')
    amount = request.form.get('amount')
    due_date = request.form.get('due_date')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO tagihan (contract_id, period, amount, due_date, status)
            VALUES (%s, %s, %s, %s, 'UNPAID')
        ''', (contract_id, period, amount, due_date))
        conn.commit()
        flash('Tagihan baru berhasil dibuat.', 'success')
    except Exception as e:
        conn.rollback()
        flash('Gagal membuat tagihan.', 'danger')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('admin_tagihan'))

@app.route('/admin/keluhan')
@login_required
def admin_keluhan():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT k.*, ph.full_name as tenant_name, km.room_number 
        FROM keluhan k
        JOIN penghuni ph ON k.tenant_id = ph.id
        JOIN kamar km ON k.room_id = km.id
        ORDER BY k.id DESC
    ''')
    keluhan = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin/keluhan.html', keluhan=keluhan)

@app.route('/admin/keluhan/proses/<int:id>', methods=['POST'])
@login_required
def admin_keluhan_proses(id):
    status = request.form.get('status') # IN_PROGRESS atau RESOLVED
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE keluhan SET status = %s WHERE id = %s", (status, id))
        conn.commit()
        flash('Status keluhan diperbarui.', 'success')
    except Exception as e:
        conn.rollback()
        flash('Gagal memperbarui keluhan.', 'danger')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('admin_keluhan'))

# --- KONTRAK SEWA ROUTES ---
@app.route('/admin/kontrak')
@login_required
def admin_kontrak():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT ks.*, ph.full_name as tenant_name, k.room_number, l.nama_lokasi
        FROM kontrak_sewa ks
        JOIN penghuni ph ON ks.tenant_id = ph.id
        JOIN kamar k ON ks.room_id = k.id
        JOIN lokasi_kos l ON k.location_id = l.id
        ORDER BY ks.id DESC
    ''')
    kontrak = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin/kontrak.html', kontrak=kontrak)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
