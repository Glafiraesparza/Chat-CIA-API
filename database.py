
import sqlite3
from pathlib import Path

# Ubicación de la base de datos
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database" / "chat.db"
SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"


def conectar_db():
    # Establece conexión con SQLite
    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row

    # Habilita las claves foráneas
    conexion.execute("PRAGMA foreign_keys = ON")

    return conexion


def inicializar_db():
    # Crea la carpeta si no existe
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conexion = conectar_db()

    # Ejecuta el script SQL
    with open(SCHEMA_PATH, "r", encoding="utf-8") as archivo:
        conexion.executescript(archivo.read())

    conexion.commit()
    conexion.close()

    print("Base de datos inicializada correctamente")


if __name__ == "__main__":
    inicializar_db()
