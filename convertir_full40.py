"""Conversor de etiquetas Full para rollo doble banda de 4 × 2,5 cm.

Mercado Libre descarga las etiquetas de producto en una hoja A4 (formato 4 × 2,5 cm).
Este conversor las acomoda de a dos por fila en una hoja de 83 × 25 mm:
40 mm de etiqueta + 3 mm vacíos en el medio + 40 mm de etiqueta.
"""
import sys
import fitz  # PyMuPDF

MM = 72 / 25.4

LABEL_W_MM = 40.0
LABEL_H_MM = 25.0
TOL_MM = 3.0

GAP_MM = 3.0
PAGE_W_MM = LABEL_W_MM * 2 + GAP_MM   # 83 mm
PAGE_H_MM = LABEL_H_MM


def encontrar_etiquetas(page):
    """Rectángulos de ~40 × 25 mm, en orden de lectura."""
    candidatos = []
    for d in page.get_drawings():
        r = d["rect"]
        if abs(r.width / MM - LABEL_W_MM) < TOL_MM and abs(r.height / MM - LABEL_H_MM) < TOL_MM:
            candidatos.append(fitz.Rect(r))
    unicos = []
    for r in candidatos:
        if not any(abs(r.x0 - u.x0) < 1 and abs(r.y0 - u.y0) < 1 for u in unicos):
            unicos.append(r)
    unicos.sort(key=lambda r: (round(r.y0 / 5), r.x0))
    return unicos


def convertir(path_entrada, path_salida):
    doc_in = fitz.open(path_entrada)
    if len(doc_in) == 0:
        raise ValueError("El PDF de entrada no tiene páginas.")
    etiquetas = [(pidx, r) for pidx, page in enumerate(doc_in) for r in encontrar_etiquetas(page)]
    total = len(etiquetas)
    if total == 0:
        raise ValueError(
            "Este archivo no parece haber sido generado con la opción 4 × 2,5 cm de Mercado Libre. "
            "Volvé a descargar las etiquetas en ese formato y subí el nuevo PDF.")

    doc_out = fitz.open()
    w_pt, h_pt, gap_pt = LABEL_W_MM * MM, LABEL_H_MM * MM, GAP_MM * MM
    xs = [0, w_pt + gap_pt]
    for i in range(0, total, 2):
        pagina = doc_out.new_page(width=PAGE_W_MM * MM, height=PAGE_H_MM * MM)
        for slot, (pidx, rect) in enumerate(etiquetas[i:i + 2]):
            destino = fitz.Rect(xs[slot], 0, xs[slot] + w_pt, h_pt)
            pagina.show_pdf_page(destino, doc_in, pidx, clip=rect)
    doc_out.save(path_salida, garbage=3, deflate=True)
    doc_out.close()
    doc_in.close()
    return total, (total + 1) // 2


if __name__ == "__main__":
    entrada = sys.argv[1] if len(sys.argv) > 1 else "Entrada.pdf"
    salida = sys.argv[2] if len(sys.argv) > 2 else "Etiquetas-Full-4x2,5-Doble-TagShip.pdf"
    total, paginas = convertir(entrada, salida)
    print(f"OK: {total} etiquetas -> {paginas} páginas -> {salida}")
