# app.py
import sqlite3, hashlib, secrets, io
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify
from datetime import datetime, date, timedelta
import pandas as pd

DB_FILE = "clinica.db"
SECRET_KEY = secrets.token_hex(16)

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Especialidades, doctores y seguros
SPECIALTIES = [
    "Medicina Interna","Medicina general","Endocrinología","Gastroenterología",
    "dermatología","Neurología","Cardiología","Otorrinolaringología",
    "pediatria","neumología","urología","nefrología"
]

DOCTORS = {
    "Medicina Interna": ["(Opcional)","Dr. Alejandro Vargas","Dra. Sofía Benítez","Dr. Javier Soto"],
    "Medicina general": ["(Opcional)","Dra. Isabela Morales","Dr. Daniel Ríos","Dra. Laura Ortega"],
    "Endocrinología": ["(Opcional)","Dra. Ana Pérez","Dr. Carlos Mendoza","Dra. Valeria Castro"],
    "Gastroenterología": ["(Opcional)","Dr. Gabriel Navarro","Dra. Carolina Jiménez","Dr. Ricardo Flores"],
    "dermatología": ["(Opcional)","Dra. Andrea García","Dr. Martín Soto","Dra. Julia Torres"],
    "Neurología": ["(Opcional)","Dr. Alejandro Morales","Dr. Javier Ortiz","Dr. Daniel Vargas"],
    "Cardiología": ["(Opcional)","Dra. Sofía Ramírez","Dra. Valeria Acosta","Dra. Isabel Flores"],
    "Otorrinolaringología": ["(Opcional)","Dra. Julia Mendoza","Dr. Miguel Pérez","Dr. Fernando Navarro"],
    "pediatria": ["(Opcional)","Dr. Rafael Torres","Dra. Elena Ortega","Dra. Julia Mendoza"],
    "neumología": ["(Opcional)","Dr. David Hernández","Dra. Victoria Soto","Dra. Marina Vargas"],
    "urología": ["(Opcional)","Dr. Rodrigo Morales","Dra. Mónica Rosas","Dr. Sergio Ramos"],
    "nefrología": ["(Opcional)","Dra. Patricia Benítez","Dr. Gabriel Acosta","Dra. Diana Herrera"]
}

INSURANCES = ["Particular","Mercantil Seguros","La Previsora","Seguros Caracas","MAPFRE","Humanitas"]

# ---------- Helpers DB ----------
def get_db():
    con = sqlite3.connect(DB_FILE)
    con.row_factory = sqlite3.Row
    return con

def hash_with_salt(password, salt):
    return hashlib.sha256((salt + password).encode('utf-8')).hexdigest()

def compute_age(dob_str):
    try:
        dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
    except Exception:
        return None
    today = date.today()
    years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return years

def generate_reg_number():
    today_str = date.today().strftime("%Y%m%d")
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) FROM patients WHERE created_at LIKE ?", (f"{date.today().isoformat()}%",))
    count = cur.fetchone()[0] + 1
    con.close()
    return f"MN-{today_str}-{count:04d}"

def login_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return fn(*args, **kwargs)
    return wrapper

# ---------- Rutas Auth ----------
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','')
        con = get_db()
        cur = con.cursor()
        cur.execute("SELECT id, full_name, password_hash, salt FROM employees WHERE username = ?", (username,))
        row = cur.fetchone()
        con.close()
        if row:
            _id, full_name, pwh, salt = row
            if hash_with_salt(password, salt) == pwh:
                session['user_id'] = _id
                session['username'] = username
                session['full_name'] = full_name
                return redirect(url_for('dashboard'))
        flash("Usuario o contraseña incorrectos", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ---------- Dashboard ----------
@app.route('/')
@login_required
def dashboard():
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) FROM patients")
    total_patients = cur.fetchone()[0]
    # Próximas citas (hasta 3 días)
    today = date.today()
    end = today + timedelta(days=3)
    cur.execute("""
      SELECT a.id, a.fecha, a.hora, a.especialidad, a.doctor, p.reg_number, p.primer_nombre, p.primer_apellido
      FROM appointments a JOIN patients p ON a.patient_id = p.id
      WHERE date(a.fecha) BETWEEN date(?) AND date(?)
      ORDER BY a.fecha, a.hora
    """, (today.isoformat(), end.isoformat()))
    upcoming = cur.fetchall()
    con.close()
    return render_template('dashboard.html', total_patients=total_patients, upcoming=upcoming)

# ---------- Pacientes ----------
@app.route('/patients')
@login_required
def patients():
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM patients ORDER BY created_at DESC")
    rows = cur.fetchall()
    con.close()
    return render_template('patients.html', patients=rows)

@app.route('/patients/new', methods=['GET','POST'])
@login_required
def patient_new():
    if request.method == 'POST':
        form = request.form
        reg_number = generate_reg_number()
        fields = {
            'reg_number': reg_number,
            'primer_nombre': form.get('primer_nombre','').strip(),
            'segundo_nombre': form.get('segundo_nombre','').strip(),
            'primer_apellido': form.get('primer_apellido','').strip(),
            'segundo_apellido': form.get('segundo_apellido','').strip(),
            'ced_prefijo': form.get('ced_prefijo','V'),
            'ced_numero': form.get('ced_numero','').strip(),
            'fecha_nacimiento': form.get('fecha_nacimiento',''),
            'edad': compute_age(form.get('fecha_nacimiento','')) or None,
            'telefono': form.get('telefono','').strip(),
            'telefono_domicilio': form.get('telefono_domicilio','').strip(),
            'direccion': form.get('direccion','').strip(),
            'seguro': form.get('seguro',''),
            'poliza': form.get('poliza','').strip(),
            'responsable': form.get('responsable','').strip(),
            'antecedentes': form.get('antecedentes','').strip(),
            'created_at': datetime.now().isoformat()
        }
        con = get_db()
        cur = con.cursor()
        cur.execute("""
           INSERT INTO patients (reg_number, primer_nombre, segundo_nombre, primer_apellido, segundo_apellido,
                                 ced_prefijo, ced_numero, fecha_nacimiento, edad, telefono, telefono_domicilio,
                                 direccion, seguro, poliza, responsable, antecedentes, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, tuple(fields.values()))
        con.commit()
        con.close()
        flash("Paciente registrado con éxito", "success")
        return redirect(url_for('patients'))
    # GET
    default_reg = generate_reg_number()
    return render_template('patient_form.html', patient=None, reg_number=default_reg, insurances=INSURANCES)

@app.route('/patients/<int:pid>/edit', methods=['GET','POST'])
@login_required
def patient_edit(pid):
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM patients WHERE id = ?", (pid,))
    patient = cur.fetchone()
    if not patient:
        con.close()
        flash("Paciente no encontrado", "danger")
        return redirect(url_for('patients'))
    if request.method == 'POST':
        f = request.form
        edad = compute_age(f.get('fecha_nacimiento',''))
        cur.execute("""
          UPDATE patients SET primer_nombre=?, segundo_nombre=?, primer_apellido=?, segundo_apellido=?, 
          ced_prefijo=?, ced_numero=?, fecha_nacimiento=?, edad=?, telefono=?, telefono_domicilio=?, direccion=?,
          seguro=?, poliza=?, responsable=?, antecedentes=?
          WHERE id=?
        """, (
            f.get('primer_nombre','').strip(),
            f.get('segundo_nombre','').strip(),
            f.get('primer_apellido','').strip(),
            f.get('segundo_apellido','').strip(),
            f.get('ced_prefijo',''),
            f.get('ced_numero','').strip(),
            f.get('fecha_nacimiento',''),
            edad,
            f.get('telefono','').strip(),
            f.get('telefono_domicilio','').strip(),
            f.get('direccion','').strip(),
            f.get('seguro',''),
            f.get('poliza','').strip(),
            f.get('responsable','').strip(),
            f.get('antecedentes','').strip(),
            pid
        ))
        con.commit()
        con.close()
        flash("Paciente actualizado", "success")
        return redirect(url_for('patients'))
    con.close()
    return render_template('patient_form.html', patient=patient, reg_number=patient['reg_number'], insurances=INSURANCES)

@app.route('/patients/<int:pid>/delete', methods=['POST'])
@login_required
def patient_delete(pid):
    con = get_db()
    cur = con.cursor()
    cur.execute("DELETE FROM patients WHERE id = ?", (pid,))
    con.commit()
    con.close()
    flash("Paciente eliminado", "warning")
    return redirect(url_for('patients'))

# ---------- Appointments ----------
@app.route('/appointments')
@login_required
def appointments():
    con = get_db()
    cur = con.cursor()
    cur.execute("""
      SELECT a.id, a.fecha, a.hora, a.especialidad, a.doctor, a.motivo, p.reg_number, p.primer_nombre, p.primer_apellido
      FROM appointments a LEFT JOIN patients p ON a.patient_id = p.id
      ORDER BY a.fecha DESC, a.hora DESC
    """)
    rows = cur.fetchall()
    con.close()
    return render_template('appointments.html', appointments=rows)

@app.route('/appointments/new', methods=['GET','POST'])
@login_required
def appointment_new():
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT id, reg_number, primer_nombre, primer_apellido FROM patients ORDER BY primer_apellido")
    patients = cur.fetchall()
    con.close()
    if request.method == 'POST':
        f = request.form
        patient_id = int(f.get('patient_id'))
        reg_number = f.get('reg_number')
        especialidad = f.get('especialidad')
        doctor = f.get('doctor')
        fecha = f.get('fecha')
        hora = f.get('hora')
        motivo = f.get('motivo','').strip()
        con = get_db()
        cur = con.cursor()
        cur.execute("""
          INSERT INTO appointments (patient_id, reg_number, especialidad, fecha, hora, doctor, motivo, created_at)
          VALUES (?,?,?,?,?,?,?,?)
        """, (patient_id, reg_number, especialidad, fecha, hora, doctor, motivo, datetime.now().isoformat()))
        con.commit()
        con.close()
        flash("Cita agendada", "success")
        return redirect(url_for('appointments'))
    # GET
    time_slots = ["09:00","10:00","11:00","13:00","14:00","15:00","16:00"]
    return render_template('appointment_form.html', patients=patients, specialties=SPECIALTIES, doctors=DOCTORS, times=time_slots)

@app.route('/appointments/<int:aid>/delete', methods=['POST'])
@login_required
def appointment_delete(aid):
    con = get_db()
    cur = con.cursor()
    cur.execute("DELETE FROM appointments WHERE id = ?", (aid,))
    con.commit()
    con.close()
    flash("Cita eliminada", "warning")
    return redirect(url_for('appointments'))

# API helper: obtener paciente en JSON
@app.route('/api/patient/<int:pid>')
@login_required
def api_patient(pid):
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM patients WHERE id = ?", (pid,))
    p = cur.fetchone()
    con.close()
    if not p:
        return jsonify({"error":"not found"}), 404
    data = dict(p)
    return jsonify(data)

# Exportar pacientes a Excel (pandas)
@app.route('/export/patients')
@login_required
def export_patients():
    con = get_db()
    df = pd.read_sql_query("SELECT reg_number, primer_nombre, segundo_nombre, primer_apellido, segundo_apellido, ced_prefijo, ced_numero, fecha_nacimiento, edad, telefono, telefono_domicilio, direccion, seguro, poliza, responsable, antecedentes, created_at FROM patients ORDER BY created_at DESC", con)
    con.close()
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Pacientes')
    output.seek(0)
    filename = f"pacientes_{date.today().isoformat()}.xlsx"
    return send_file(output, download_name=filename, as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# ---------- Run ----------
if __name__ == "__main__":
    app.run(debug=True)
