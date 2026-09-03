import sys
import fitz  # PyMuPDF

MM = 72 / 25.4  # puntos por mm

# Tamaño de la etiqueta de Correo Argentino dentro de la hoja A4 apaisada
LABEL_W_MM = 86.0
LABEL_H_MM = 163.0
TOL_MM = 3.0

PAGE_W_MM = 100.0
PAGE_H_MM = 150.0


def encontrar_etiqueta(page):
    """Detecta el rectángulo vectorial que corresponde al borde de la
    etiqueta de Correo Argentino (~86 x 163 mm) dentro de la página."""
    drawings = page.get_drawings()
    candidatos = []
    for d in drawings:
        r = d["rect"]
        w_mm = r.width / MM
        h_mm = r.height / MM
        if abs(w_mm - LABEL_W_MM) < TOL_MM and abs(h_mm - LABEL_H_MM) < TOL_MM:
            candidatos.append(r)

    if not candidatos:
        return None

    # si hay varios trazos casi idénticos (borde dibujado más de una vez),
    # nos quedamos con el primero
    candidatos.sort(key=lambda r: (r.y0, r.x0))
    return candidatos[0]


def convertir(path_entrada, path_salida):
    doc_in = fitz.open(path_entrada)
    if len(doc_in) == 0:
        raise ValueError("El PDF de entrada no tiene páginas.")

    doc_out = fitz.open()
    page_w_pt = PAGE_W_MM * MM
    page_h_pt = PAGE_H_MM * MM

    procesadas = 0
    for pidx, page in enumerate(doc_in):
        rect = encontrar_etiqueta(page)
        if rect is None:
            raise ValueError(
                "No pudimos reconocer la etiqueta de Correo Argentino en la "
                f"página {pidx + 1}. Verificá que sea el PDF de etiquetas "
                "descargado de Correo Argentino, sin editar."
            )

        out_page = doc_out.new_page(width=page_w_pt, height=page_h_pt)
        target = fitz.Rect(0, 0, page_w_pt, page_h_pt)
        out_page.show_pdf_page(
            target,
            doc_in,
            pidx,
            clip=rect,
        )
        procesadas += 1

    assert procesadas == len(doc_in), (
        f"Entrada={len(doc_in)} páginas, Salida={procesadas} páginas: no coinciden"
    )
    for p in doc_out:
        w_mm = p.rect.width / MM
        h_mm = p.rect.height / MM
        assert abs(w_mm - PAGE_W_MM) < 0.5 and abs(h_mm - PAGE_H_MM) < 0.5, \
            f"Página con tamaño incorrecto: {w_mm}x{h_mm}"

    doc_out.save(path_salida)
    doc_out.close()
    doc_in.close()
    return procesadas


if __name__ == "__main__":
    entrada = sys.argv[1] if len(sys.argv) > 1 else "Entrada.pdf"
    salida = sys.argv[2] if len(sys.argv) > 2 else "Etiquetas-Correo-TagShip.pdf"
    total = convertir(entrada, salida)
    print(f"OK: {total} páginas -> {salida}")
