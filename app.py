from flask import Flask, render_template, request, jsonify, redirect, session
import os
from datetime import datetime
import psycopg2
import psycopg2.extras

app = Flask(__name__)
app.secret_key = "clave_super_secreta"

DATABASE_URL = os.environ.get("DATABASE_URL")

# ==============================
# CONEXIÓN A SUPABASE
# ==============================

def get_db():
    if not DATABASE_URL:
        raise Exception("DATABASE_URL no configurada")
    return psycopg2.connect(DATABASE_URL, sslmode="require")


# ==============================
# CREAR TABLAS SI NO EXISTEN
# ==============================

def init_db():
    try:
        conn = get_db()
        cur = conn.cursor()

        # Tabla registros
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

        # Tabla catálogo
        cur.execute("""
            CREATE TABLE IF NOT EXISTS catalogo (
                id SERIAL PRIMARY KEY,
                tipo TEXT,
                valor TEXT
            );
        """)

        # Insertar valores por defecto si no existen
        cur.execute("SELECT COUNT(*) FROM catalogo;")
        total = cur.fetchone()[0]

        if total == 0:
            valores = [
                ("accesorio","Mouse"),
                ("accesorio","Headset"),
                ("accesorio","Backpack"),
                ("modelo","Logitech G203"),
                ("modelo","HP Victus"),
                ("modelo","Dell G15")
            ]
            for v in valores:
                cur.execute("INSERT INTO catalogo (tipo, valor) VALUES (%s,%s)", v)

        conn.commit()
        cur.close()
        conn.close()

        print("Base de datos lista")

    except Exception as e:
        print("Error inicializando DB:", e)


# Ejecutar al iniciar
with app.app_context():
    init_db()


# ==============================
# VISTAS
# ==============================

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


# ==============================
# API REGISTROS
# ==============================

@app.route("/api/registros")
def registros():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT * FROM registros WHERE estado='activo'")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([dict(r) for r in rows])


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
            data["id"].strip(),
            data["accesorio"],
            data["modelo"],
            data["nombre"],
            data["poo"],
            data["factura"],
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ))
        conn.commit()

    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({"error":"ID ya existe"}),400

    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({"error":str(e)}),500

    cur.close()
    conn.close()
    return jsonify({"status":"ok"})


@app.route("/api/entregado/<id>", methods=["PUT"])
def entregar(id):
    if not session.get("admin"):
        return jsonify({"error":"No autorizado"}),403

    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE registros SET estado='entregado' WHERE id=%s",(id,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status":"ok"})


@app.route("/api/eliminar/<id>", methods=["DELETE"])
def eliminar(id):
    if not session.get("admin"):
        return jsonify({"error":"No autorizado"}),403

    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE registros SET estado='eliminado' WHERE id=%s",(id,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status":"ok"})


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


# ==============================
# API CATALOGO
# ==============================

@app.route("/api/catalogo")
def catalogo():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT * FROM catalogo ORDER BY tipo")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([dict(r) for r in rows])


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


# ==============================
# RUN (para desarrollo local)
# ==============================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)