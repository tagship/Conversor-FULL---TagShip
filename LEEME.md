# TagStudio: cómo subirlo a Render

Este paquete convierte tu conversor actual (conversor-full-tagship.onrender.com) en TagStudio:
Diseños personalizados + Etiquetas Full + (pronto) Recortar PDF, todo en la misma página.

## Qué cambia en tu repositorio de GitHub

- app.py → REEMPLAZAR por el de este paquete.
- studio/index.html → AGREGAR (carpeta nueva "studio").
- convertir_full.py → es el mismo que ya tenés, no cambia.

No borres nada más: convertir_normales.py, requirements.txt, Procfile y la carpeta static/
siguen igual. La carpeta templates/ queda sin usar (podés dejarla).

## Pasos

1. Entrá a tu repositorio en github.com.
2. Tocá "Add file" → "Upload files".
3. Arrastrá el archivo app.py y la carpeta studio completa (con su index.html adentro).
4. Abajo, tocá "Commit changes".
5. Render detecta el cambio y vuelve a publicar solo (tarda 2 o 3 minutos).
   Si no lo hace: en Render, entrá al servicio → "Manual Deploy" → "Deploy latest commit".

## Direcciones

- https://conversor-full-tagship.onrender.com/      → TagStudio (Diseños)
- https://conversor-full-tagship.onrender.com/full  → directo a Etiquetas Full
- https://conversor-full-tagship.onrender.com/recortar  → directo a Recortar PDF
