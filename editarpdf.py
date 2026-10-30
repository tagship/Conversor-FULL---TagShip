"""Editar PDF: convierte una página de un PDF en elementos editables para el editor de TagStudio.

- Los textos se sacan como datos (texto, posición, tamaño, color, negrita) para volverlos editables.
- Todo lo demás (líneas, recuadros, códigos, logos) se manda como imagen sin los textos, en alta resolución.
- Si la hoja es grande (por ejemplo A4 con la etiqueta en un costado), se recorta sola la etiqueta.
"""
import io
import os
import base64
import uuid
import traceback

import fitz  # PyMuPDF
from flask import Blueprint, request, jsonify

bp = Blueprint("editarpdf", __name__)
MM = 72 / 25.4
DPI = 300


def _zona(page):
    """Zona a editar: el recuadro de la etiqueta si hay uno, o el contenido de la hoja."""
    pr = page.rect
    cands = []
    for d in page.get_drawings():
        r = d["rect"]
        if r.width > 40 * MM and r.height > 40 * MM and r.width < pr.width * 0.92 and r.height < pr.height * 0.98:
            cands.append(fitz.Rect(r))
    for info in page.get_image_info():
        r = fitz.Rect(info["bbox"])
        if r.width > 40 * MM and r.height > 40 * MM and r.width < pr.width * 0.92 and r.height < pr.height * 0.98:
            cands.append(r)
    if cands and pr.width > 110 * MM:
        r = max(cands, key=lambda x: x.get_area())
        return fitz.Rect(r.x0 - 1.5 * MM, r.y0 - 1.5 * MM, r.x1 + 1.5 * MM, r.y1 + 1.5 * MM) & pr
    if pr.width <= 110 * MM:
        return fitz.Rect(pr)
    # sin recuadro: todo lo que tenga contenido, salvo líneas que cruzan la hoja entera
    caja = fitz.Rect()
    for d in page.get_drawings():
        r = d["rect"]
        if r.width < pr.width * 0.9:
            caja |= r
    for b in page.get_text("dict")["blocks"]:
        caja |= fitz.Rect(b["bbox"])
    for info in page.get_image_info():
        caja |= fitz.Rect(info["bbox"])
    if caja.is_empty:
        return fitz.Rect(pr)
    return fitz.Rect(caja.x0 - 2 * MM, caja.y0 - 2 * MM, caja.x1 + 2 * MM, caja.y1 + 2 * MM) & pr


def preparar(path, pagina=0):
    doc = fitz.open(path)
    if len(doc) == 0:
        raise ValueError("El PDF no tiene páginas.")
    pagina = max(0, min(int(pagina), len(doc) - 1))
    page = doc[pagina]
    zona = _zona(page)

    textos, rects = [], []
    for b in page.get_text("dict", clip=zona)["blocks"]:
        for line in b.get("lines", []):
            wdir = line.get("dir", (1, 0))
            for sp in line.get("spans", []):
                t = sp.get("text", "")
                if not t.strip():
                    continue
                bb = fitz.Rect(sp["bbox"])
                rects.append(bb)
                font = sp.get("font", "")
                flags = sp.get("flags", 0)
                textos.append({
                    "texto": t,
                    "x": (bb.x0 - zona.x0) / MM, "y": (bb.y0 - zona.y0) / MM,
                    "w": bb.width / MM, "h": bb.height / MM,
                    "tam": sp.get("size", 10) / MM,          # tamaño de letra en mm
                    "fuente": font,
                    "negrita": bool(flags & 16) or any(k in font.lower() for k in ("bold", "bld", "black", "heavy", "semib", "demi")),
                    "cursiva": bool(flags & 2) or "italic" in font.lower() or "oblique" in font.lower(),
                    "color": "#%06x" % sp.get("color", 0),
                    "rotado": abs(wdir[0] - 1) > 0.01,
                })
    # quitar los textos del dibujo (quedan líneas, recuadros, códigos e imágenes)
    for r in rects:
        page.add_redact_annot(r)
    if rects:
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE,
                              graphics=fitz.PDF_REDACT_LINE_ART_NONE,
                              text=fitz.PDF_REDACT_TEXT_REMOVE)
    # el resto (líneas, recuadros, códigos, logos) se manda como imagen de alta resolución sin los textos;
    # el editor la separa en elementos sueltos que se pueden mover, borrar o reemplazar
    pix = page.get_pixmap(clip=zona, dpi=DPI, alpha=False)
    fondo = base64.b64encode(pix.tobytes("png")).decode()
    res = {"ancho": zona.width / MM, "alto": zona.height / MM, "fondo": fondo, "dpi": DPI, "textos": textos,
           "paginas": len(doc), "pagina": pagina}
    doc.close()
    return res


@bp.post("/pdf/editable")
def pdf_editable():
    archivo = request.files.get("archivo")
    if not archivo or archivo.filename == "":
        return jsonify(error="No se recibió ningún archivo."), 400
    if not archivo.filename.lower().endswith(".pdf"):
        return jsonify(error="El archivo debe ser un PDF."), 400
    base = os.path.dirname(os.path.abspath(__file__))
    tmp = os.path.join(base, "uploads"); os.makedirs(tmp, exist_ok=True)
    entrada = os.path.join(tmp, uuid.uuid4().hex + ".pdf")
    archivo.save(entrada)
    try:
        return jsonify(preparar(entrada, request.form.get("pagina", 0)))
    except ValueError as e:
        return jsonify(error=str(e)), 422
    except Exception:
        traceback.print_exc()
        return jsonify(error="No pudimos abrir ese PDF para editarlo. Probá con otro archivo."), 422
    finally:
        if os.path.exists(entrada):
            os.remove(entrada)
