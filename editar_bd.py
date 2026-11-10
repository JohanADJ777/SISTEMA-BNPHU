"""Agregar, modificar o borrar datos de la base desde Python y ver el resultado.

Usa la misma base que la aplicación (src/config.py: bnphu.db). Lo que se cambia
aquí se ve en DB Browser (con F5) y en VS Code, y al revés.
"""

import sqlite3

from src.config import RUTA_BD

conexion = sqlite3.connect(str(RUTA_BD))
print(f"Base de datos: {RUTA_BD}")

# Agregar (solo si todavía no existe, para que no se repita cada vez que se ejecuta)
conexion.execute(
    "INSERT INTO autor (nombre, apellido) "
    "SELECT ?, ? WHERE NOT EXISTS (SELECT 1 FROM autor WHERE nombre = ? AND apellido = ?)",
    ("Johan", "Almanzar", "Johan", "Almanzar"),
)

# Modificar (quita el # de la línea de abajo para usarlo)
# conexion.execute("UPDATE autor SET apellido = ? WHERE id_autor = ?", ("Sánchez", 3))

# Borrar (quita el # de la línea de abajo para usarlo)
# conexion.execute("DELETE FROM autor WHERE id_autor = ?", (19,))

conexion.commit()

for fila in conexion.execute("SELECT * FROM autor"):
    print(tuple(fila))

conexion.close()
