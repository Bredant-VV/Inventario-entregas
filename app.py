from flask import Flask, render_template, request, jsonify, redirect, session
import os
from datetime import datetime
import psycopg2
import psycopg2.extras

app = Flask(__name__)
app.secret_key = "clave_super_secreta"

DATABASE_URL = os.environ.get("DATABASE_URL")

# ---------------- CONEXIÓN ----------------

def get_db():
    if not DATABASE_URL:
        raise Exception("DATABASE_URL no configurada")
    return psycopg2.connect(DATABASE_URL, sslmode="require")

# ---------------- CREAR TABLAS ----------------

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS registros (
            id TEXT PRIMARY KEY,
            accesorio TEXT,
            modelo TEXT,
            nombre TEXT,
            poo TEXT,
            factura TEXT,
            estado TEXT,
            fecha TEXT
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS catalogo (
            id SERIAL PRIMARY KEY,
            tipo TEXT,
            valor TEXT
        );
    """)

    # Insertar catálogo inicial si está vacío
    cur.execute("SELECT COUNT(*) FROM catalogo;")
    total = cur.fetchone()[0]

    if total == 0:
        defaults = [
            ('accesorio','Mouse'),
            ('accesorio','Headset'),
            ('accesorio','Backpack'),
            ('modelo','Logitech G203'),
            ('modelo','HP Victus'),
            ('modelo','Dell G15')
        ]
        for d in defaults:
            cur.execute("INSERT INTO catalogo (tipo, valor) VALUES (%s,%s)", d)

    conn.commit()
    cur.close()
    conn.close()

with app.app_context():
    init_db()

# ---------------- VISTAS ----------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == "admin123":
            session["admin"] = True
            return redirect("/admin")
    return render_template("login.html")

@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect("/login")
    return render_template("admin.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- API REGISTROS ----------------

# 🔹 Activos (estos son los que ve el usuario en "Mis entregas")
@app.route("/api/registros")
def registros():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("""
        SELECT * FROM registros
        WHERE estado = 'activo'
        ORDER BY fecha DESC
    """)

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify([dict(r) for r in rows])

# 🔹 Agregar registro
@app.route("/api/agregar", methods=["POST"])
def agregar():
    if not session.get("admin"):
        return jsonify({"error":"No autorizado"}),403

    data = request.json
    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO registros 
            (id, accesorio, modelo, nombre, poo, factura, estado, fecha)
            VALUES (%s,%s,%s,%s,%s,%s,'activo',%s)
        """,(
            data["id"],
            data["accesorio"],
            data["modelo"],
            data["nombre"],
            data["poo"],
            data["factura"],
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ))
        conn.commit()
    except Exception:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({"error":"ID ya existe"}),400

    cur.close()
    conn.close()
    return jsonify({"status":"ok"})

# 🔹 Marcar como entregado (desaparece del usuario)
@app.route("/api/entregado/<id>", methods=["PUT"])
def entregar(id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE registros
        SET estado = 'entregado'
        WHERE id = %s
    """,(id,))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"status":"ok"})

# 🔹 Eliminar
@app.route("/api/eliminar/<id>", methods=["DELETE"])
def eliminar(id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE registros
        SET estado = 'eliminado'
        WHERE id = %s
    """,(id,))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"status":"ok"})

# 🔹 Buscar por POO o Factura
@app.route("/api/buscar/<valor>")
def buscar(valor):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("""
        SELECT * FROM registros
        WHERE poo = %s OR factura = %s
    """,(valor,valor))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify([dict(r) for r in rows])

# ---------------- API CATALOGO ----------------

@app.route("/api/catalogo")
def catalogo():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("SELECT tipo, valor FROM catalogo")
    rows = cur.fetchall()

    cur.close()
    conn.close()

    accesorios = [r["valor"] for r in rows if r["tipo"] == "accesorio"]
    modelos = [r["valor"] for r in rows if r["tipo"] == "modelo"]

    return jsonify({
        "accesorios": accesorios,
        "modelos": modelos
    })

@app.route("/api/catalogo", methods=["POST"])
def agregar_catalogo():
    if not session.get("admin"):
        return jsonify({"error":"No autorizado"}),403

    data = request.json
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO catalogo (tipo, valor)
        VALUES (%s,%s)
    """,(data["tipo"], data["valor"]))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"status":"ok"})

# ---------------- SERVIDOR ----------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)