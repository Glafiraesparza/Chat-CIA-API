
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import httpx
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from database import conectar_db, inicializar_db

CIA_API_URL = "http://127.0.0.1:8000"


@asynccontextmanager
async def lifespan(app: FastAPI):
    inicializar_db()
    yield


app = FastAPI(
    title="Chat Seguro API",
    lifespan=lifespan
)

# Archivos estáticos de la interfaz
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def inicio():
    return FileResponse("static/index.html")


class MensajeRequest(BaseModel):
    remitente_id: int
    destinatario_id: int
    mensaje: str


@app.get("/usuarios")
def obtener_usuarios():
    conexion = conectar_db()
    try:
        usuarios = conexion.execute(
            "SELECT id, nombre FROM usuarios"
        ).fetchall()
        return [dict(usuario) for usuario in usuarios]
    finally:
        conexion.close()


@app.post("/mensajes")
async def enviar_mensaje(datos: MensajeRequest):
    if not datos.mensaje.strip():
        raise HTTPException(400, "El mensaje no puede estar vacío")

    if datos.remitente_id == datos.destinatario_id:
        raise HTTPException(400, "Selecciona otro destinatario")

    conexion = conectar_db()

    try:
        usuarios = conexion.execute(
            "SELECT id FROM usuarios WHERE id IN (?, ?)",
            (datos.remitente_id, datos.destinatario_id)
        ).fetchall()

        if len(usuarios) != 2:
            raise HTTPException(404, "Usuario no encontrado")

        # 1. CIFRAR el mensaje mediante la CIA API
        async with httpx.AsyncClient(timeout=10) as cliente:
            respuesta = await cliente.post(
                f"{CIA_API_URL}/confidentiality/encrypt",
                json={"message": datos.mensaje}
            )
            respuesta.raise_for_status()
            mensaje_cifrado = respuesta.json()["ciphertext"]

            # 2. FIRMAR el mensaje cifrado
            respuesta = await cliente.post(
                f"{CIA_API_URL}/integrity/sign",
                json={"message": mensaje_cifrado}
            )
            respuesta.raise_for_status()
            firma = respuesta.json()["signature"]

        # 3. GUARDAR en la base de datos SQLite
        fecha = datetime.now(timezone.utc).isoformat()

        cursor = conexion.execute(
            """
            INSERT INTO mensajes
            (remitente_id, destinatario_id,
             mensaje_cifrado, firma, fecha_envio)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                datos.remitente_id,
                datos.destinatario_id,
                mensaje_cifrado,
                firma,
                fecha
            )
        )
        conexion.commit()

        return {
            "id": cursor.lastrowid,
            "mensaje": "Mensaje cifrado, firmado y guardado",
            "fecha_envio": fecha
        }

    except httpx.HTTPError:
        raise HTTPException(502, "Error al comunicarse con CIA API")
    finally:
        conexion.close()


@app.get("/mensajes")
def obtener_mensajes(usuario_id: int, contacto_id: int):
    conexion = conectar_db()

    try:
        # 4. CONSULTAR mensajes directamente desde SQLite
        mensajes = conexion.execute(
            """
            SELECT id, remitente_id, destinatario_id,
                   mensaje_cifrado, firma, fecha_envio
            FROM mensajes
            WHERE
                (remitente_id = ? AND destinatario_id = ?)
                OR
                (remitente_id = ? AND destinatario_id = ?)
            ORDER BY fecha_envio ASC, id ASC
            """,
            (usuario_id, contacto_id, contacto_id, usuario_id)
        ).fetchall()

        return [
            {**dict(mensaje), "estado": "No verificado"}
            for mensaje in mensajes
        ]

    finally:
        conexion.close()


# 5. DESCIFRAR un mensaje usando la CIA API
@app.post("/mensajes/{mensaje_id}/descifrar")
async def descifrar_mensaje(mensaje_id: int):
    conexion = conectar_db()

    try:
        mensaje = conexion.execute(
            "SELECT mensaje_cifrado FROM mensajes WHERE id = ?",
            (mensaje_id,)
        ).fetchone()

        if not mensaje:
            raise HTTPException(404, "Mensaje no encontrado")

        async with httpx.AsyncClient(timeout=10) as cliente:
            respuesta = await cliente.post(
                f"{CIA_API_URL}/confidentiality/decrypt",
                json={"ciphertext": mensaje["mensaje_cifrado"]}
            )
            respuesta.raise_for_status()

        return {"texto": respuesta.json()["plaintext"]}

    except httpx.HTTPError:
        raise HTTPException(502, "Error al descifrar con CIA API")
    finally:
        conexion.close()


# 6. VERIFICAR la integridad mediante la CIA API
@app.post("/mensajes/{mensaje_id}/verificar")
async def verificar_mensaje(mensaje_id: int):
    conexion = conectar_db()

    try:
        mensaje = conexion.execute(
            """
            SELECT mensaje_cifrado, firma
            FROM mensajes WHERE id = ?
            """,
            (mensaje_id,)
        ).fetchone()

        if not mensaje:
            raise HTTPException(404, "Mensaje no encontrado")

        async with httpx.AsyncClient(timeout=10) as cliente:
            respuesta = await cliente.post(
                f"{CIA_API_URL}/integrity/verify",
                json={
                    "message": mensaje["mensaje_cifrado"],
                    "signature": mensaje["firma"]
                }
            )
            respuesta.raise_for_status()

        return {"valid": respuesta.json()["valid"]}

    except httpx.HTTPError:
        raise HTTPException(502, "Error al verificar con CIA API")
    finally:
        conexion.close()
