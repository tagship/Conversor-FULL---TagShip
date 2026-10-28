"""Etiquetas Full en formato 5 × 2,5 cm → hojas de 10 × 15 con 10 etiquetas cada una.

Se acomodan en 2 columnas × 5 filas, a tamaño original (sin achicar), con el espacio
sobrante repartido entre las filas para poder cortar cómodo con tijera.
"""
import sys
import fitz  # PyMuPDF

from convertir_full import encontrar_etiquetas, MM, LABEL_W_MM, LABEL_H_MM

HOJA_W_MM, HOJA_H_MM = 100.0, 150.0
COLUMNAS, FILAS = 2, 5
POR_HOJA = COLUMNAS * FILAS


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

    w, h = LABEL_W_MM * MM, LABEL_H_MM * MM
    gap_x = (HOJA_W_MM - COLUMNAS * LABEL_W_MM) / (COLUMNAS + 1) * MM
    gap_y = (HOJA_H_MM - FILAS * LABEL_H_MM) / (FILAS + 1) * MM
    doc_out = fitz.open()
    for i in range(0, total, POR_HOJA):
        pagina = doc_out.new_page(width=HOJA_W_MM * MM, height=HOJA_H_MM * MM)
        for n, (pidx, rect) in enumerate(etiquetas[i:i + POR_HOJA]):
            fila, col = divmod(n, COLUMNAS)
            x = gap_x + col * (w + gap_x)
            y = gap_y + fila * (h + gap_y)
            pagina.show_pdf_page(fitz.Rect(x, y, x + w, y + h), doc_in, pidx, clip=rect)
    doc_out.save(path_salida, garbage=3, deflate=True)
    doc_out.close()
    doc_in.close()
    return total, (total + POR_HOJA - 1) // POR_HOJA


if __name__ == "__main__":
    entrada = sys.argv[1] if len(sys.argv) > 1 else "Entrada.pdf"
    salida = sys.argv[2] if len(sys.argv) > 2 else "Etiquetas-Full-10xhoja-TagShip.pdf"
    total, paginas = convertir(entrada, salida)
    print(f"OK: {total} etiquetas -> {paginas} hojas -> {salida}")
