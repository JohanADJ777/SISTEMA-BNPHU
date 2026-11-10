"""Configuración general del proyecto.

Aquí se guardan los valores que se usan en varias partes del programa.
"""

from pathlib import Path

NOMBRE_PROYECTO = "Sistema de préstamos BNPHU"
VERSION = "1.0.0"

# Carpeta raíz del proyecto y rutas importantes
RAIZ = Path(__file__).resolve().parent.parent
RUTA_ESQUEMA = RAIZ / "sql" / "esquema.sql"
RUTA_DATOS = RAIZ / "sql" / "datos.sql"
RUTA_BD = RAIZ / "bnphu.db"  # archivo de la base de datos SQLite

# Días que dura un préstamo si no se indica otra cosa
DIAS_PRESTAMO = 7
