import os
import uuid
import traceback

from flask import Flask, request, send_file, send_from_directory, jsonify

import convertir_normales
import convertir_full

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STUDIO_DIR = os.path.join(BASE_DIR, "studio")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

MAX_MB = 15

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_MB * 1024 * 1024


@app.route("/")
def index():
    # TagShip Studio: Diseños, Etiquetas Full y (pronto) Recortar PDF
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
