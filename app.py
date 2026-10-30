import os
import uuid
import traceback

from flask import Flask, request, send_file, send_from_directory, jsonify, redirect

import convertir_normales
import convertir_full
import convertir_full_simple
import convertir_normales10

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STUDIO_DIR = os.path.join(BASE_DIR, "studio")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

MAX_MB = 15

app = Flask(__name__)

# Activación de cuentas (Google + número de compra de Mercado Libre)
from cuentas import bp as cuentas_bp
app.register_blueprint(cuentas_bp)

# Editar PDF (convierte una página en elementos editables)
from editarpdf import bp as editarpdf_bp
app.register_blueprint(editarpdf_bp)

# Recortes automáticos (PAQ.AR y Bultos para Full)
from recortes import bp as recortes_bp
app.register_blueprint(recortes_bp)
app.config["MAX_CONTENT_LENGTH"] = MAX_MB * 1024 * 1024


# Si este servicio tiene la variable REDIRECT_TO (ej: https://tagstudio.onrender.com),
# manda todas las visitas a la dirección nueva. Sirve para que el link viejo siga funcionando.
@app.before_request
def redirigir_a_nueva_direccion():
    destino = os.environ.get("REDIRECT_TO", "").strip().rstrip("/")
    if destino:
        url = destino + request.full_path.rstrip("?")
        return redirect(url, code=301 if request.method == "GET" else 307)


@app.route("/")
def index():
    # TagStudio: pantalla de inicio
    resp = send_from_directory(STUDIO_DIR, "index.html")
    resp.headers["Cache-Control"] = "no-cache"
    return resp


@app.route("/manifest.webmanifest")
def manifest():
    resp = send_from_directory(STUDIO_DIR, "manifest.webmanifest", mimetype="application/manifest+json")
    resp.headers["Cache-Control"] = "no-cache"
    return resp


@app.route("/sw.js")
def service_worker():
    resp = send_from_directory(STUDIO_DIR, "sw.js", mimetype="application/javascript")
    resp.headers["Cache-Control"] = "no-cache"
    resp.headers["Service-Worker-Allowed"] = "/"
    return resp


@app.route("/icons/<path:nombre>")
def iconos(nombre):
    return send_from_directory(os.path.join(STUDIO_DIR, "icons"), nombre, max_age=86400)


@app.route("/descargas/<path:nombre>")
def descargas(nombre):
    # Archivos para descargar (por ejemplo, la extensión de Chrome para PAQ.AR)
    return send_from_directory(os.path.join(STUDIO_DIR, "descargas"), nombre, as_attachment=True)


@app.route("/disenos")
def disenos():
    # Enlace directo a Diseños personalizados
    resp = send_from_directory(STUDIO_DIR, "index.html")
    resp.headers["Cache-Control"] = "no-cache"
    return resp


@app.route("/cola")
def cola():
    # Enlace directo a la Cola de impresión (ideal para el modo estación)
    resp = send_from_directory(STUDIO_DIR, "index.html")
    resp.headers["Cache-Control"] = "no-cache"
    return resp


@app.route("/recortar")
def recortar():
    # Enlace directo a la sección Recortar PDF del Studio
    resp = send_from_directory(STUDIO_DIR, "index.html")
    resp.headers["Cache-Control"] = "no-cache"
    return resp


@app.route("/full")
def full():
    # Enlace directo a la sección Etiquetas Full del Studio
    resp = send_from_directory(STUDIO_DIR, "index.html")
    resp.headers["Cache-Control"] = "no-cache"
    return resp


@app.route("/convertir/normales", methods=["POST"])
def convertir_normales_endpoint():
    archivo = request.files.get("archivo")
    if not archivo or archivo.filename == "":
        return jsonify({"error": "No se recibió ningún archivo."}), 400
    if not archivo.filename.lower().endswith(".pdf"):
        return jsonify({"error": "El archivo debe ser un PDF."}), 400

    job_id = uuid.uuid4().hex
    entrada_path = os.path.join(UPLOAD_DIR, f"{job_id}.pdf")
    salida_path = os.path.join(OUTPUT_DIR, f"{job_id}.pdf")
    archivo.save(entrada_path)

    try:
        total, paginas = convertir_normales.convertir(entrada_path, salida_path)
    except ValueError as e:
        return jsonify({"error": str(e)}), 422
    except Exception:
        traceback.print_exc()
        return jsonify({
            "error": "No pudimos abrir ese archivo. Verificá que sea el PDF "
                     "de etiquetas descargado de Mercado Libre (formato 6 × 4 cm) "
                     "sin editar."
        }), 422
    finally:
        if os.path.exists(entrada_path):
            os.remove(entrada_path)

    return send_file(
        salida_path,
        as_attachment=True,
        download_name="Etiquetas-TagShip.pdf",
        mimetype="application/pdf",
    )


@app.route("/convertir/full-doble", methods=["POST"])
def convertir_full_doble_endpoint():
    archivo = request.files.get("archivo")
    if not archivo or archivo.filename == "":
        return jsonify({"error": "No se recibió ningún archivo."}), 400
    if not archivo.filename.lower().endswith(".pdf"):
        return jsonify({"error": "El archivo debe ser un PDF."}), 400

    job_id = uuid.uuid4().hex
    entrada_path = os.path.join(UPLOAD_DIR, f"{job_id}.pdf")
    salida_path = os.path.join(OUTPUT_DIR, f"{job_id}.pdf")
    archivo.save(entrada_path)

    try:
        total, paginas = convertir_full.convertir(entrada_path, salida_path)
    except ValueError as e:
        return jsonify({"error": str(e)}), 422
    except Exception:
        traceback.print_exc()
        return jsonify({
            "error": "No pudimos abrir ese archivo. Verificá que sea el PDF "
                     "de etiquetas descargado de Mercado Libre (formato 5 × 2.5 cm) "
                     "sin editar."
        }), 422
    finally:
        if os.path.exists(entrada_path):
            os.remove(entrada_path)

    return send_file(
        salida_path,
        as_attachment=True,
        download_name="Etiquetas-Full-Doble-TagShip.pdf",
        mimetype="application/pdf",
    )


@app.route("/convertir/full-simple", methods=["POST"])
def convertir_full_simple_endpoint():
    """Etiquetas Full 5 × 2,5 cm → rollo simple banda (una etiqueta de 50 × 25 mm por página)."""
    archivo = request.files.get("archivo")
    if not archivo or archivo.filename == "":
        return jsonify({"error": "No se recibió ningún archivo."}), 400
    if not archivo.filename.lower().endswith(".pdf"):
        return jsonify({"error": "El archivo debe ser un PDF."}), 400

    job_id = uuid.uuid4().hex
    entrada_path = os.path.join(UPLOAD_DIR, f"{job_id}.pdf")
    salida_path = os.path.join(OUTPUT_DIR, f"{job_id}.pdf")
    archivo.save(entrada_path)
    try:
        convertir_full_simple.convertir(entrada_path, salida_path)
    except ValueError as e:
        return jsonify({"error": str(e)}), 422
    except Exception:
        traceback.print_exc()
        return jsonify({
            "error": "No pudimos abrir ese archivo. Verificá que sea el PDF de etiquetas "
                     "descargado de Mercado Libre (formato 5 × 2.5 cm) sin editar."
        }), 422
    finally:
        if os.path.exists(entrada_path):
            os.remove(entrada_path)

    return send_file(
        salida_path,
        as_attachment=True,
        download_name="Etiquetas-Full-Simple-TagShip.pdf",
        mimetype="application/pdf",
    )


@app.route("/convertir/normales-10", methods=["POST"])
def convertir_normales10_endpoint():
    """Etiquetas Full 5 × 2,5 cm → 10 por hoja de 10 × 15."""
    archivo = request.files.get("archivo")
    if not archivo or archivo.filename == "":
        return jsonify({"error": "No se recibió ningún archivo."}), 400
    if not archivo.filename.lower().endswith(".pdf"):
        return jsonify({"error": "El archivo debe ser un PDF."}), 400

    job_id = uuid.uuid4().hex
    entrada_path = os.path.join(UPLOAD_DIR, f"{job_id}.pdf")
    salida_path = os.path.join(OUTPUT_DIR, f"{job_id}.pdf")
    archivo.save(entrada_path)
    try:
        convertir_normales10.convertir(entrada_path, salida_path)
    except ValueError as e:
        return jsonify({"error": str(e)}), 422
    except Exception:
        traceback.print_exc()
        return jsonify({
            "error": "No pudimos abrir ese archivo. Verificá que sea el PDF de etiquetas "
                     "descargado de Mercado Libre (formato 5 × 2.5 cm) sin editar."
        }), 422
    finally:
        if os.path.exists(entrada_path):
            os.remove(entrada_path)

    return send_file(
        salida_path,
        as_attachment=True,
        download_name="Etiquetas-Full-10xhoja-TagShip.pdf",
        mimetype="application/pdf",
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
