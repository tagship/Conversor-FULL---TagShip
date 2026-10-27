"""Activación de cuentas de TagStudio con el número de compra de Mercado Libre.

Configuración (en Render → Environment):
  FIREBASE_SERVICE_ACCOUNT   JSON completo de la clave privada de Firebase (obligatorio)
  ADMIN_KEY                  una contraseña tuya, para conectar Mercado Libre
  ML_CLIENT_ID / ML_CLIENT_SECRET   datos de tu aplicación de Mercado Libre
  ML_PRECIO_MINIMO_IMPRESORA (opcional) precio mínimo de un ítem para contar como impresora. Por defecto 100000
  MAX_CUENTAS_POR_COMPRA     (opcional) cuántas cuentas puede activar un mismo número. Por defecto 2
  BASE_URL                   (opcional) dirección pública. Por defecto https://tagstudio.onrender.com

Mientras Mercado Libre no esté conectado, se acepta cualquier número con formato válido
y queda registrado como "sin_verificar". Apenas conectás Mercado Libre, la verificación es real.
"""
import os
import re
import json
import time
import hashlib
import threading
import traceback
from urllib.parse import quote

import requests
from flask import Blueprint, request, jsonify, redirect

import firebase_admin
from firebase_admin import credentials, auth as fb_auth, firestore

bp = Blueprint("cuentas", __name__)

ML_API = "https://api.mercadolibre.com"
ML_ID = os.environ.get("ML_CLIENT_ID", "").strip()
ML_SECRET = os.environ.get("ML_CLIENT_SECRET", "").strip()
ADMIN_KEY = os.environ.get("ADMIN_KEY", "").strip()
BASE_URL = os.environ.get("BASE_URL", "https://tagstudio.onrender.com").strip().rstrip("/")
REDIRECT_URI = BASE_URL + "/ml/callback"
MAX_CUENTAS = int(os.environ.get("MAX_CUENTAS_POR_COMPRA", "2") or 2)
PRECIO_MIN = float(os.environ.get("ML_PRECIO_MINIMO_IMPRESORA", "100000") or 100000)

_db = None
_tok = {"access": None, "exp": 0, "seller": None}
_lock = threading.Lock()


def db():
    """Cliente de Firestore con permisos de servidor (o None si falta la clave)."""
    global _db
    if _db is None:
        raw = os.environ.get("FIREBASE_SERVICE_ACCOUNT", "").strip()
        if not raw:
            return None
        if not firebase_admin._apps:
            firebase_admin.initialize_app(credentials.Certificate(json.loads(raw)))
        _db = firestore.client()
    return _db


# ---------------- Mercado Libre ----------------

def ml_conectado():
    d = db()
    if not (ML_ID and ML_SECRET and d):
        return False
    return d.collection("config").document("ml").get().exists


def ml_token():
    """Access token vigente. Lo renueva solo con el refresh token guardado."""
    with _lock:
        if _tok["access"] and time.time() < _tok["exp"] - 120:
            return _tok["access"]
        ref = db().collection("config").document("ml")
        snap = ref.get()
        if not snap.exists:
            raise RuntimeError("Mercado Libre no está conectado")
        r = requests.post(
            ML_API + "/oauth/token",
            data={
                "grant_type": "refresh_token",
                "client_id": ML_ID,
                "client_secret": ML_SECRET,
                "refresh_token": snap.to_dict().get("refresh_token"),
            },
            headers={"accept": "application/json"},
            timeout=20,
        )
        if r.status_code != 200:
            raise RuntimeError("No se pudo renovar el token de ML: " + r.text[:300])
        j = r.json()
        # Mercado Libre entrega un refresh token nuevo cada vez: hay que guardarlo
        ref.set(
            {"refresh_token": j["refresh_token"], "user_id": j.get("user_id"),
             "actualizado": firestore.SERVER_TIMESTAMP},
            merge=True,
        )
        _tok.update(access=j["access_token"], exp=time.time() + int(j.get("expires_in", 21600)),
                    seller=j.get("user_id"))
        return _tok["access"]


def ml_get(path):
    return requests.get(ML_API + path, headers={"Authorization": "Bearer " + ml_token()}, timeout=20)


def verificar_compra(numero):
    """(True, "") si el número es una compra pagada de una impresora a tu cuenta."""
    ordenes = []
    r = ml_get(f"/orders/{numero}")
    if r.status_code == 200:
        ordenes = [r.json()]
    else:
        # Si compró varias cosas juntas, Mercado Libre puede mostrarle el número de "paquete"
        p = ml_get(f"/packs/{numero}")
        if p.status_code == 200:
            for o in p.json().get("orders", []):
                rr = ml_get(f"/orders/{o.get('id')}")
                if rr.status_code == 200:
                    ordenes.append(rr.json())
    if not ordenes:
        return False, ("No encontramos esa compra. Revisá el número en Mercado Libre, "
                       "en Mis compras → detalle de la compra.")
    seller = _tok.get("seller")
    for o in ordenes:
        if seller and str((o.get("seller") or {}).get("id")) != str(seller):
            continue
        if o.get("status") != "paid":
            continue
        for it in o.get("order_items", []):
            if float(it.get("unit_price") or 0) >= PRECIO_MIN:
                return True, ""
    return False, ("Ese número de compra no corresponde a una impresora TagShip "
                   "o la compra fue cancelada.")


# ---------------- Activación ----------------

@bp.post("/api/activar")
def activar():
    d = db()
    if not d:
        return jsonify(error="La activación todavía no está configurada en el servidor."), 503
    h = request.headers.get("Authorization", "")
    if not h.startswith("Bearer "):
        return jsonify(error="Iniciá sesión con Google primero."), 401
    try:
        info = fb_auth.verify_id_token(h[7:])
    except Exception:
        return jsonify(error="Tu sesión venció. Volvé a iniciar sesión con Google."), 401
    uid, email = info["uid"], info.get("email", "")

    acc = d.collection("access").document(uid)
    snap = acc.get()
    if snap.exists and snap.to_dict().get("activa"):
        return jsonify(ok=True)

    numero = re.sub(r"\D", "", str((request.get_json(silent=True) or {}).get("orden", "")))
    if not 10 <= len(numero) <= 20:
        return jsonify(error="El número de compra tiene que tener entre 10 y 20 números."), 400

    aref = d.collection("activations").document(numero)
    a = aref.get()
    uids = (a.to_dict() or {}).get("uids", []) if a.exists else []
    if uid not in uids and len(uids) >= MAX_CUENTAS:
        return jsonify(error="Ese número de compra ya se usó para activar otra cuenta. "
                             "Si es un error, escribinos por WhatsApp."), 409

    if ml_conectado():
        try:
            ok, motivo = verificar_compra(numero)
        except Exception:
            traceback.print_exc()
            return jsonify(error="No pudimos verificar la compra con Mercado Libre. "
                                 "Probá de nuevo en unos minutos."), 502
        if not ok:
            return jsonify(error=motivo), 422
        fuente = "mercadolibre"
    else:
        fuente = "sin_verificar"

    aref.set({"uids": firestore.ArrayUnion([uid]), "emails": firestore.ArrayUnion([email]),
              "fuente": fuente, "actualizado": firestore.SERVER_TIMESTAMP}, merge=True)
    acc.set({"activa": True, "orden": numero, "email": email, "fuente": fuente,
             "fecha": firestore.SERVER_TIMESTAMP})
    return jsonify(ok=True)


# ---------------- Conectar Mercado Libre (una sola vez) ----------------

def _state():
    return hashlib.sha256(("tagstudio:" + ADMIN_KEY).encode()).hexdigest()[:32]


@bp.get("/ml/conectar")
def ml_conectar():
    if not ADMIN_KEY or request.args.get("clave", "") != ADMIN_KEY:
        return "No autorizado.", 403
    if not ML_ID:
        return "Falta configurar ML_CLIENT_ID en Render.", 500
    url = ("https://auth.mercadolibre.com.ar/authorization?response_type=code"
           f"&client_id={ML_ID}&redirect_uri={quote(REDIRECT_URI, safe='')}&state={_state()}")
    return redirect(url)


@bp.get("/ml/callback")
def ml_callback():
    if not ADMIN_KEY or request.args.get("state", "") != _state():
        return "No autorizado.", 403
    code = request.args.get("code", "")
    if not code:
        return "Mercado Libre no devolvió el código. Probá de nuevo.", 400
    d = db()
    if not d:
        return "Falta configurar FIREBASE_SERVICE_ACCOUNT en Render.", 500
    r = requests.post(
        ML_API + "/oauth/token",
        data={"grant_type": "authorization_code", "client_id": ML_ID, "client_secret": ML_SECRET,
              "code": code, "redirect_uri": REDIRECT_URI},
        headers={"accept": "application/json"},
        timeout=20,
    )
    if r.status_code != 200:
        return "No se pudo conectar Mercado Libre: " + r.text[:300], 502
    j = r.json()
    d.collection("config").document("ml").set(
        {"refresh_token": j["refresh_token"], "user_id": j.get("user_id"),
         "conectado": firestore.SERVER_TIMESTAMP}, merge=True)
    _tok.update(access=j["access_token"], exp=time.time() + int(j.get("expires_in", 21600)),
                seller=j.get("user_id"))
    return ("<h2 style='font-family:sans-serif'>Listo: Mercado Libre quedó conectado a TagStudio.</h2>"
            "<p style='font-family:sans-serif'>Desde ahora los números de compra se verifican solos. "
            "Ya podés cerrar esta pestaña.</p>")


@bp.get("/api/estado-activacion")
def estado():
    """Diagnóstico simple (sin datos privados)."""
    return jsonify(servidor=bool(db()), mercadolibre=ml_conectado())
