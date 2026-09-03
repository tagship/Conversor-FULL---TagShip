# Conversor de etiquetas TagShip

Web que convierte los PDF de etiquetas de Mercado Libre al tamaño que
imprime tu impresora térmica TagShip.

- **Herramienta 1 (activa):** etiquetas normales (6×4 cm de ML) → hojas de
  100×150 mm con 4 etiquetas cada una.
- **Herramienta 2:** etiquetas Full dobles — todavía no implementada
  (el botón queda deshabilitado con la leyenda "Próximamente").

No usa inteligencia artificial en el procesamiento: recorta, rota y
escala el PDF por geometría. Corre instantáneo y no tiene costo por uso.

## Estructura

```
app.py                 servidor Flask (rutas y validaciones)
convertir_normales.py  lógica de conversión (PyMuPDF)
templates/index.html   página (HTML + CSS + JS, sin frameworks)
requirements.txt       dependencias Python
Procfile                comando de arranque para Render/Railway
```

## Probarlo en tu computadora

```
pip install -r requirements.txt
python app.py
```

Abrí `http://127.0.0.1:5000` en el navegador.

## Subirlo a internet (Render, plan gratuito)

1. Creá una cuenta en https://render.com
2. Subí esta carpeta a un repositorio de GitHub (podés arrastrar los
   archivos desde github.com/new sin usar la terminal)
3. En Render: **New > Web Service** → conectá ese repositorio
4. Configuración:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
   - **Plan:** Free
5. Render te va a dar una URL tipo `tagship-etiquetas.onrender.com`
6. Desde el admin de Tiendanube (Configuración > Dominios), agregá el
   subdominio `etiquetas.tagship.ar` y apuntalo a esa URL de Render con
   un registro CNAME (Tiendanube te va a guiar en ese paso, porque son
   ellos quienes administran la zona DNS de tagship.ar)

**Nota sobre el plan gratuito de Render:** el servidor "se duerme" tras
unos minutos sin uso y tarda ~30 segundos en despertar en la primera
visita del día. Si eso molesta a tus clientes, el plan pago (desde
USD 7/mes) lo mantiene siempre activo.

## Cómo sumar la Herramienta 2 (etiquetas Full)

Cuando esté lista, va en un archivo nuevo `convertir_full.py` con la
misma estructura que `convertir_normales.py`, conectado a la ruta que
ya existe en `app.py` (`/convertir/full`), y el panel de la web se
activa sacando la clase `soon` y agregando su propio dropzone —ya está
todo preparado para eso, solo falta la lógica de conversión.
