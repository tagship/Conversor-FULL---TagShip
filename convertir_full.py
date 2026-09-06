import sys
import fitz  # PyMuPDF

MM = 72 / 25.4  # puntos por mm

LABEL_W_MM = 50.0
LABEL_H_MM = 25.0
TOL_MM = 3.0  # tolerancia para matchear rectángulos ~50x25

PAGE_W_MM = 103.0  # ancho del rollo de doble banda
PAGE_H_MM = 25.0
GAP_MM = 3.0  # margen vacío en el medio entre las dos etiquetas
HALF_W_MM = (PAGE_W_MM - GAP_MM) / 2  # 50.0


def encontrar_etiquetas(page):
    """Detecta los rectángulos vectoriales que corresponden a una etiqueta
    de ~50 x 25 mm (formato 5x2.5cm de Mercado Libre), ordenados en orden
    de lectura (fila por fila, izquierda a derecha)."""
    drawings = page.get_drawings()
    candidatos = []
    for d in drawings:
        r = d["rect"]
        w_mm = r.width / MM
        h_mm = r.height / MM
        if abs(w_mm - LABEL_W_MM) < TOL_MM and abs(h_mm - LABEL_H_MM) < TOL_MM:
            candidatos.append(r)

    # deduplicar rectángulos casi idénticos (por si el PDF dibuja el borde
    # con más de un trazo)
    unicos = []
    for r in candidatos:
        dup = False
        for u in unicos:
            if abs(r.x0 - u.x0) < 1 and abs(r.y0 - u.y0) < 1:
                dup = True
                break
        if not dup:
            unicos.append(r)

    # orden de lectura: por fila (y0, agrupando filas cercanas) y luego x0
    unicos.sort(key=lambda r: (round(r.y0 / 5), r.x0))
    return unicos


def convertir(path_entrada, path_salida):
    doc_in = fitz.open(path_entrada)
    if len(doc_in) == 0:
        raise ValueError("El PDF de entrada no tiene páginas.")

    todas_etiquetas = []  # lista de (page_index, rect)
    for pidx, page in enumerate(doc_in):
        rects = encontrar_etiquetas(page)
        for r in rects:
            todas_etiquetas.append((pidx, r))

    total = len(todas_etiquetas)
    if total == 0:
        raise ValueError(
            "Este archivo no parece haber sido generado con la opción "
            "5 × 2.5 cm de Mercado Libre. Volvé a descargar las etiquetas "
            "seleccionando el formato 5 × 2.5 cm y subí el nuevo PDF."
        )

    doc_out = fitz.open()
    page_w_pt = PAGE_W_MM * MM
    page_h_pt = PAGE_H_MM * MM
    half_w_pt = HALF_W_MM * MM
    gap_pt = GAP_MM * MM

    # posiciones de los 2 espacios (x0) en la página de salida, dejando el
    # margen del medio (gap_pt) vacío
    posiciones_x = [0, half_w_pt + gap_pt]

    colocadas = 0
    for i in range(0, total, 2):
        grupo = todas_etiquetas[i:i + 2]
        out_page = doc_out.new_page(width=page_w_pt, height=page_h_pt)
        for slot, (pidx, rect) in enumerate(grupo):
            x0 = posiciones_x[slot]
            target = fitz.Rect(x0, 0, x0 + half_w_pt, page_h_pt)
            out_page.show_pdf_page(
                target,
                doc_in,
                pidx,
                clip=rect,
            )
            colocadas += 1

    assert colocadas == total, f"Entrada={total} Salida={colocadas} no coinciden"
    for p in doc_out:
        w_mm = p.rect.width / MM
        h_mm = p.rect.height / MM
        assert abs(w_mm - PAGE_W_MM) < 0.5 and abs(h_mm - PAGE_H_MM) < 0.5, \
            f"Página con tamaño incorrecto: {w_mm}x{h_mm}"

    doc_out.save(path_salida)
    doc_out.close()
    doc_in.close()
    return total, len(range(0, total, 2))


if __name__ == "__main__":
    entrada = sys.argv[1] if len(sys.argv) > 1 else "Entrada.pdf"
    salida = sys.argv[2] if len(sys.argv) > 2 else "Etiquetas-Full-Doble-TagShip.pdf"
    total, paginas = convertir(entrada, salida)
    print(f"OK: {total} etiquetas -> {paginas} páginas -> {salida}")
