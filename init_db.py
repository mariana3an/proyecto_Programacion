# init_db.py
import sqlite3
import secrets, hashlib
from datetime import datetime

DB_FILE = "clinica.db"

def hash_with_salt(password, salt):
    return hashlib.sha256((salt + password).encode('utf-8')).hexdigest()

def init_db():
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    # employees
    cur.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        full_name TEXT,
        password_hash TEXT,
        salt TEXT
    );
    """)
    # patients
    cur.execute("""
    CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reg_number TEXT UNIQUE,
        primer_nombre TEXT,
        segundo_nombre TEXT,
        primer_apellido TEXT,
        segundo_apellido TEXT,
        ced_prefijo TEXT,
        ced_numero TEXT,
        fecha_nacimiento TEXT,
        edad INTEGER,
        telefono TEXT,
        telefono_domicilio TEXT,
        direccion TEXT,
        seguro TEXT,
        poliza TEXT,
        responsable TEXT,
        antecedentes TEXT,
        created_at TEXT
    );
    """)
    # appointments
    cur.execute("""
    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        reg_number TEXT,
        especialidad TEXT,
        fecha TEXT,
        hora TEXT,
        doctor TEXT,
        motivo TEXT,
        created_at TEXT,
        FOREIGN KEY(patient_id) REFERENCES patients(id)
    );
    """)
    con.commit()

    # crear usuario mariana si no existe
    cur.execute("SELECT id FROM employees WHERE username = ?", ("mariana",))
    if not cur.fetchone():
        salt = secrets.token_hex(8)
        pwd = "admin123"
        ph = hash_with_salt(pwd, salt)
        cur.execute("INSERT INTO employees (username, full_name, password_hash, salt) VALUES (?,?,?,?)",
                    ("mariana", "Mariana Nuñez", ph, salt))
        con.commit()
        print("Usuario 'mariana' creado con password 'admin123' (cámbiala luego).")
    con.close()

if __name__ == "__main__":
    init_db()
    print("DB inicializada.")
