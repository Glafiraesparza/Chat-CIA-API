
PRAGMA foreign_keys = ON;

-- Tabla de usuarios
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE
);

-- Tabla de mensajes
CREATE TABLE IF NOT EXISTS mensajes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    remitente_id INTEGER NOT NULL,
    destinatario_id INTEGER NOT NULL,
    mensaje_cifrado TEXT NOT NULL,
    firma TEXT NOT NULL,
    fecha_envio TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (remitente_id) REFERENCES usuarios(id),
    FOREIGN KEY (destinatario_id) REFERENCES usuarios(id),

    CHECK (remitente_id != destinatario_id)
);

-- Usuarios de prueba
INSERT OR IGNORE INTO usuarios (id, nombre)
VALUES (1, 'Alice');

INSERT OR IGNORE INTO usuarios (id, nombre)
VALUES (2, 'Bob');
