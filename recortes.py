"""Recortes automáticos de TagStudio: PAQ.AR (Correo Argentino) y Bultos para Full.

Los dos vienen en una hoja A4 con la etiqueta en un costado. Se detecta el recuadro de
cada etiqueta (por sus líneas o por la imagen que la forma) y se pasa a una hoja de
10 × 15 cm, sin deformarla y sin perder calidad (sigue siendo vectorial).
"""
import io
import os
import uuid
import traceback

import fitz  # PyMuPDF
from flask import Blueprint, request, send_file, jsonify

bp = Blueprint("recortes", __name__)

MM = 72 / 25.4
SALIDA_W, SALIDA_H = 100 * MM, 150 * MM
BORDE = 0.8 * MM  # margen extra alrededor del recuadro, para no cortar la línea del borde

TIPOS = {
    "paqar": {
        "nombre": "PAQ.AR",
        "archivo": "Etiquetas-PAQAR-10x15-TagShip.pdf",
        "error": "No encontramos la etiqueta de PAQ.AR en ese PDF. Subí el archivo tal cual lo "
                 "descargaste de Correo Argentino, sin editar.",
    },
    "bultos": {
        "nombre": "Bultos para Full",
        "archivo": "Bultos-Full-10x15-TagShip.pdf",
        "error": "No encontramos la etiqueta de bultos en ese PDF. Subí el archivo tal cual lo "
                 "descargaste de Mercado Libre, sin editar.",
    },
}


def _candidatos(page):
    """Rectángulos del tamaño de una etiqueta: recuadros dibujados o imágenes grandes."""
    pr = page.rect
    rects = []
    for d in page.get_drawings():
        r = d["rect"]
        if r.width > 50 * MM and r.height > 70 * MM and r.width < pr.width * 0.9 and r.height < pr.height * 0.98:
            rects.append(fitz.Rect(r))
    for info in page.get_image_info():
        r = fitz.Rect(info["bbox"])
        if r.width > 50 * MM and r.height > 70 * MM and r.width < pr.width * 0.9 and r.height < pr.height * 0.98:
            rects.append(r)
    # sacar duplicados (el mismo recuadro dibujado varias veces)
    unicos = []
    for r in sorted(rects, key=lambda x: -x.get_area()):
        if any(abs(r.x0 - u.x0) < 3 * MM and abs(r.y0 - u.y0) < 3 * MM and
               abs(r.x1 - u.x1) < 3 * MM and abs(r.y1 - u.y1) < 3 * MM for u in unicos):
            continue
        # si está adentro de otro más grande, es una parte de la etiqueta: se descarta
        if any(u.contains(r) for u in unicos):
            continue
        unicos.append(r)
    unicos.sort(key=lambda r: (round(r.y0 / (20 * MM)), r.x0))
    return unicos


def recortar(path_entrada, path_salida, tipo):
    doc_in = fitz.open(path_entrada)
    if len(doc_in) == 0:
        raise ValueError("El PDF no tiene páginas.")
    etiquetas = []
    for pno, page in enumerate(doc_in):
        for r in _candidatos(page):
            etiquetas.append((pno, r))
    if not etiquetas:
        raise ValueError(TIPOS[tipo]["error"])

    doc_out = fitz.open()
    for pno, r in etiquetas:
        clip = fitz.Rect(r.x0 - BORDE, r.y0 - BORDE, r.x1 + BORDE, r.y1 + BORDE) & doc_in[pno].rect
        pagina = doc_out.new_page(width=SALIDA_W, height=SALIDA_H)
        girar = 90 if clip.width > clip.height else 0
        # keep_proportion: se escala sin deformar y queda centrada en la hoja de 10 × 15
        pagina.show_pdf_page(pagina.rect, doc_in, pno, clip=clip, keep_proportion=True, rotate=girar)
    doc_out.save(path_salida, garbage=3, deflate=True)
    doc_out.close()
    doc_in.close()
    return len(etiquetas)


@bp.post("/recortar/<tipo>")
def recortar_endpoint(tipo):
    if tipo not in TIPOS:
        return jsonify(error="Tipo de recorte desconocido."), 404
    archivo = request.files.get("archivo")
    if not archivo or archivo.filename == "":
        return jsonify(error="No se recibió ningún archivo."), 400
    if not archivo.filename.lower().endswith(".pdf"):
        return jsonify(error="El archivo debe ser un PDF."), 400
    base = os.path.dirname(os.path.abspath(__file__))
    tmp = os.path.join(base, "uploads")
    os.makedirs(tmp, exist_ok=True)
    job = uuid.uuid4().hex
    entrada = os.path.join(tmp, f"{job}-in.pdf")
    salida = os.path.join(tmp, f"{job}-out.pdf")
    archivo.save(entrada)
    try:
        recortar(entrada, salida, tipo)
    except ValueError as e:
        return jsonify(error=str(e)), 422
    except Exception:
        traceback.print_exc()
        return jsonify(error=TIPOS[tipo]["error"]), 422
    finally:
        if os.path.exists(entrada):
            os.remove(entrada)
    # se manda desde memoria y se borra el archivo: no queda nada guardado en el servidor
    with open(salida, "rb") as fh:
        datos = io.BytesIO(fh.read())
    os.remove(salida)
    return send_file(datos, as_attachment=True, download_name=TIPOS[tipo]["archivo"],
                     mimetype="application/pdf")
