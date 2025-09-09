import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from ttkbootstrap import Style

DB_NAME = "clinic.db"

def check_login(username, password, root):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT * FROM employees WHERE username=? AND password=?", (username, password))
    user = cur.fetchone()
    conn.close()

    if user:
        messagebox.showinfo("Login correcto", "Bienvenida Mariana Núñez")
        root.destroy()
        open_dashboard()
    else:
        messagebox.showerror("Error", "Usuario o contraseña incorrectos")

def open_login():
    root = tk.Tk()
    root.title("Login - Base de Datos Mariana Nuñez C.A")
    style = Style("cosmo")  # Azul/gris moderno

    tk.Label(root, text="Usuario:").pack(pady=5)
    username_entry = tk.Entry(root)
    username_entry.pack()

    tk.Label(root, text="Contraseña:").pack(pady=5)
    password_entry = tk.Entry(root, show="*")
    password_entry.pack()

    login_btn = ttk.Button(root, text="Iniciar sesión",
                           command=lambda: check_login(username_entry.get(), password_entry.get(), root))
    login_btn.pack(pady=10)

    root.mainloop()

def open_dashboard():
    dash = tk.Tk()
    dash.title("Dashboard - Base de Datos Mariana Nuñez C.A")
    style = Style("cosmo")

    ttk.Label(dash, text="Resumen de Pacientes y Próximas Citas", font=("Arial", 14, "bold")).pack(pady=10)

    # Aquí vamos a cargar resumen de pacientes y citas
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT id, username FROM employees WHERE username=? AND password=?", (user, pwd))

    total_patients = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM appointments")
    total_appointments = cur.fetchone()[0]
    conn.close()

    ttk.Label(dash, text=f"Pacientes registrados: {total_patients}").pack(pady=5)
    ttk.Label(dash, text=f"Citas registradas: {total_appointments}").pack(pady=5)

    dash.mainloop()

if __name__ == "__main__":
    open_login()
