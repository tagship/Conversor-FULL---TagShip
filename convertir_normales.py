import sys
import fitz  # PyMuPDF

MM = 72 / 25.4  # puntos por mm

LABEL_W_MM = 60.2
LABEL_H_MM = 40.0
TOL_MM = 3.0  # tolerancia para matchear rectángulos ~60.2x40

PAGE_W_MM = 100.0
PAGE_H_MM = 150.0
QUAD_W_MM = 50.0
QUAD_H_MM = 75.0


def encontrar_etiquetas(page):
    """Detecta los rectángulos vectoriales que corresponden a una etiqueta
    de ~60.2 x 40.0 mm, ordenados en orden de lectura (fila por fila,
    izquierda a derecha)."""
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

    todas_etiquetas = []  # lista de (doc_in, page_index, rect)
    for pidx, page in enumerate(doc_in):
        w_mm = page.rect.width / MM
        h_mm = page.rect.height / MM
        if not (abs(w_mm - 210) < 3 and abs(h_mm - 297) < 3):
            raise ValueError(
                "Este archivo no parece haber sido generado con la opción "
                "6 × 4 cm de Mercado Libre (la página no es A4). Volvé a "
                "descargar las etiquetas seleccionando el formato 6 × 4 cm "
                "y subí el nuevo PDF."
            )
        rects = encontrar_etiquetas(page)
        for r in rects:
            todas_etiquetas.append((pidx, r))

    total = len(todas_etiquetas)
    if total == 0:
        raise ValueError(
            "Este archivo no parece haber sido generado con la opción "
            "6 × 4 cm de Mercado Libre. Volvé a descargar las etiquetas "
            "seleccionando el formato 6 × 4 cm y subí el nuevo PDF."
        )

    doc_out = fitz.open()
    page_w_pt = PAGE_W_MM * MM
    page_h_pt = PAGE_H_MM * MM
    quad_w_pt = QUAD_W_MM * MM
    quad_h_pt = QUAD_H_MM * MM

    # posiciones de los 4 cuadrantes (x0, y0) en la página de salida
    posiciones = [
        (0, 0),
        (quad_w_pt, 0),
        (0, quad_h_pt),
        (quad_w_pt, quad_h_pt),
    ]

    colocadas = 0
    for i in range(0, total, 4):
        grupo = todas_etiquetas[i:i + 4]
        out_page = doc_out.new_page(width=page_w_pt, height=page_h_pt)
        for slot, (pidx, rect) in enumerate(grupo):
            x0, y0 = posiciones[slot]
            target = fitz.Rect(x0, y0, x0 + quad_w_pt, y0 + quad_h_pt)
            # show_pdf_page con rotate=90 rota el contenido fuente antes de
            # encajarlo en el rectángulo destino, preservando vectores/texto
            out_page.show_pdf_page(
                target,
                doc_in,
                pidx,
                clip=rect,
                rotate=90,
            )
            colocadas += 1

    # Validaciones
    assert colocadas == total, f"Entrada={total} Salida={colocadas} no coinciden"
    for p in doc_out:
        w_mm = p.rect.width / MM
        h_mm = p.rect.height / MM
        assert abs(w_mm - PAGE_W_MM) < 0.5 and abs(h_mm - PAGE_H_MM) < 0.5, \
            f"Página con tamaño incorrecto: {w_mm}x{h_mm}"

    doc_out.save(path_salida)
    doc_out.close()
    doc_in.close()
    return total, len(range(0, total, 4))


if __name__ == "__main__":
    entrada = sys.argv[1] if len(sys.argv) > 1 else "Entrada.pdf"
    salida = sys.argv[2] if len(sys.argv) > 2 else "Etiquetas-Full-TagShip.pdf"
    total, paginas = convertir(entrada, salida)
    print(f"OK: {total} etiquetas -> {paginas} páginas -> {salida}")
