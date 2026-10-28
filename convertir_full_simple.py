"""Conversor de etiquetas Full para rollo SIMPLE banda de 5 × 2,5 cm.

Toma el PDF de Mercado Libre en formato 5 × 2,5 cm (varias etiquetas por hoja A4)
y deja una etiqueta por página de 50 × 25 mm, en orden.
"""
import sys
import fitz  # PyMuPDF

from convertir_full import encontrar_etiquetas, MM, LABEL_W_MM, LABEL_H_MM


def convertir(path_entrada, path_salida):
    doc_in = fitz.open(path_entrada)
    if len(doc_in) == 0:
        raise ValueError("El PDF de entrada no tiene páginas.")
    etiquetas = [(pidx, r) for pidx, page in enumerate(doc_in) for r in encontrar_etiquetas(page)]
    total = len(etiquetas)
    if total == 0:
        raise ValueError(
            "Este archivo no parece haber sido generado con la opción 5 × 2.5 cm de Mercado Libre. "
            "Volvé a descargar las etiquetas en ese formato y subí el nuevo PDF.")
    doc_out = fitz.open()
    w_pt, h_pt = LABEL_W_MM * MM, LABEL_H_MM * MM
    for pidx, rect in etiquetas:
        pagina = doc_out.new_page(width=w_pt, height=h_pt)
        pagina.show_pdf_page(pagina.rect, doc_in, pidx, clip=rect)
    doc_out.save(path_salida, garbage=3, deflate=True)
    doc_out.close()
    doc_in.close()
    return total, total


if __name__ == "__main__":
    entrada = sys.argv[1] if len(sys.argv) > 1 else "Entrada.pdf"
    salida = sys.argv[2] if len(sys.argv) > 2 else "Etiquetas-Full-Simple-TagShip.pdf"
    total, paginas = convertir(entrada, salida)
    print(f"OK: {total} etiquetas -> {paginas} páginas -> {salida}")
