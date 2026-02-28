from flask import Flask, render_template, request, jsonify, redirect, session
import csv
import json
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "clave_super_secreta"

CSV_FILE = "data.csv"
ENTREGADOS_FILE = "entregados.csv"
ELIMINADOS_FILE = "eliminados.csv"
CATALOGO_FILE = "catalogo.json"

FIELDS = ["id","accesorio","modelo","nombre","poo","factura","fecha"]

# =========================
# CSV UTILIDADES
# =========================

def ensure_file(file):
    if not os.path.exists(file):
        with open(file,"w",newline='',encoding="utf-8") as f:
            writer = csv.DictWriter(f,fieldnames=FIELDS)
            writer.writeheader()

def read_csv(file):
    ensure_file(file)
    with open(file,newline='',encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        for r in rows:
            if r.get("id"):
                r["id"] = r["id"].strip()
        return rows

def write_csv(file,data):
    with open(file,"w",newline='',encoding="utf-8") as f:
        writer = csv.DictWriter(f,fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(data)

def append_csv(file,row):
    ensure_file(file)
    if row.get("id"):
        row["id"] = row["id"].strip()
    with open(file,"a",newline='',encoding="utf-8") as f:
        writer = csv.DictWriter(f,fieldnames=FIELDS)
        writer.writerow(row)

# =========================
# CATALOGO
# =========================

def ensure_catalogo():
    if not os.path.exists(CATALOGO_FILE):
        default = {
            "accesorios":["Mouse","Headset","Backpack","Laptop"],
            "modelos":["Logitech G203","HP Victus","Dell G15"]
        }
        with open(CATALOGO_FILE,"w") as f:
            json.dump(default,f,indent=2)

def read_catalogo():
    ensure_catalogo()
    with open(CATALOGO_FILE) as f:
        return json.load(f)

def write_catalogo(data):
    with open(CATALOGO_FILE,"w") as f:
        json.dump(data,f,indent=2)

# =========================
# VISTAS
# =========================

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        if request.form.get("password")=="admin123":
            session["admin"]=True
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

# =========================
# API REGISTROS
# =========================

@app.route("/api/registros")
def registros():
    return jsonify(read_csv(CSV_FILE))

@app.route("/api/agregar",methods=["POST"])
def agregar():
    if not session.get("admin"):
        return jsonify({"error":"No autorizado"}),403

    data = request.json
    data["id"] = data["id"].strip()

    activos = read_csv(CSV_FILE)

    # 🚨 Validar ID único
    for r in activos:
        if r["id"] == data["id"]:
            return jsonify({"error":"ID ya existe"}),400

    data["fecha"]=datetime.now().strftime("%Y-%m-%d %H:%M")
    append_csv(CSV_FILE,data)

    return jsonify({"status":"ok"})

@app.route("/api/entregado/<id>",methods=["PUT"])
def entregar(id):
    if not session.get("admin"):
        return jsonify({"error":"No autorizado"}),403

    id = id.strip()

    activos = read_csv(CSV_FILE)
    nuevos = []
    movido = False

    for r in activos:
        if r["id"] == id and not movido:
            append_csv(ENTREGADOS_FILE,r)
            movido = True
        else:
            nuevos.append(r)

    write_csv(CSV_FILE,nuevos)
    return jsonify({"status":"ok"})

@app.route("/api/eliminar/<id>",methods=["DELETE"])
def eliminar(id):
    if not session.get("admin"):
        return jsonify({"error":"No autorizado"}),403

    id = id.strip()

    activos = read_csv(CSV_FILE)
    nuevos = []
    movido = False

    for r in activos:
        if r["id"] == id and not movido:
            append_csv(ELIMINADOS_FILE,r)
            movido = True
        else:
            nuevos.append(r)

    write_csv(CSV_FILE,nuevos)
    return jsonify({"status":"ok"})

# =========================
# API CATALOGO
# =========================

@app.route("/api/catalogo")
def catalogo():
    return jsonify(read_catalogo())

@app.route("/api/catalogo",methods=["POST"])
def agregar_catalogo():
    if not session.get("admin"):
        return jsonify({"error":"No autorizado"}),403

    data=request.json
    catalogo=read_catalogo()

    if data["tipo"] in catalogo and data["valor"] not in catalogo[data["tipo"]]:
        catalogo[data["tipo"]].append(data["valor"])
        write_catalogo(catalogo)

    return jsonify({"status":"ok"})

if __name__=="__main__":
    app.run(debug=True)