# TagStudio: cómo subirlo a Render

Archivos de este paquete (todos van en la raíz de tu repositorio de GitHub):

- app.py            → REEMPLAZAR
- cuentas.py        → NUEVO (activación de cuentas con el número de compra)
- requirements.txt  → REEMPLAZAR (suma firebase-admin y requests)
- convertir_full.py → igual que antes
- studio/index.html → REEMPLAZAR

No borres convertir_normales.py, Procfile ni la carpeta static/.

## Configuración en Render (Environment)

- FIREBASE_SERVICE_ACCOUNT: el contenido completo del archivo JSON de la clave privada de Firebase.
- ADMIN_KEY: una contraseña inventada por vos (solo para conectar Mercado Libre).
- ML_CLIENT_ID y ML_CLIENT_SECRET: los datos de tu aplicación de Mercado Libre.

Para conectar Mercado Libre (una sola vez): abrí https://tagstudio.onrender.com/ml/conectar?clave=TU_ADMIN_KEY
y tocá "Permitir" con tu cuenta de vendedor de TagShip.

Se activan solo las compras de productos con SKU tagship + número (+ letra opcional): tagship230, tagship15b, tagship56d…

Mientras Mercado Libre no esté conectado, cualquier número de compra con formato válido activa la cuenta
y queda registrado como "sin_verificar". Cuando conectes Mercado Libre, la verificación pasa a ser real.

## Direcciones

- https://tagstudio.onrender.com/          → Inicio
- https://tagstudio.onrender.com/disenos   → Diseños
- https://tagstudio.onrender.com/full      → Etiquetas Full
- https://tagstudio.onrender.com/recortar  → Recortar PDF
- https://tagstudio.onrender.com/api/estado-activacion → muestra si el servidor y Mercado Libre están configurados
