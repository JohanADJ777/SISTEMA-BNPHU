"""Prueba de conexión: abre la base de datos del proyecto y cuenta los registros de cada tabla.

Usa la misma ruta que el resto del sistema (src/config.py), así que da igual
desde qué carpeta se ejecute: siempre abre el mismo archivo bnphu.db.
"""

import sqlite3

from src.config import RUTA_BD

conexion = sqlite3.connect(str(RUTA_BD))   # aquí se establece la conexión
cursor = conexion.cursor()

print("Conexión establecida correctamente")
print(f"Archivo: {RUTA_BD}")

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
for (tabla,) in cursor.fetchall():
    cantidad = cursor.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
    print(f"Tabla: {tabla} -> {cantidad} registros")

conexion.close()
