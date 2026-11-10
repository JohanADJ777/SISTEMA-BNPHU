"""Conexión a la base de datos SQLite.

SQLite viene incluido en Python (módulo sqlite3): no hay que instalar nada.
"""

import sqlite3

from src.config import RUTA_BD, RUTA_DATOS, RUTA_ESQUEMA


def conectar(ruta=None):
    """Abre la base de datos (la crea vacía si no existe).

    Activa las llaves foráneas y hace que las filas se lean por nombre de columna.
    """
    conexion = sqlite3.connect(str(ruta or RUTA_BD))
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


def _leer(ruta):
    with open(ruta, encoding="utf-8") as archivo:
        return archivo.read()


def _ejecutar_como_una_sola_operacion(conexion, *rutas):
    """Ejecuta uno o varios archivos .sql dentro de UNA transacción.

    Si cualquier instrucción falla se deshace todo, así nunca queda una base
    a medias (por ejemplo con las tablas pero sin los empleados).
    """
    guion = "BEGIN;\n" + "\n".join(_leer(ruta) for ruta in rutas) + "\nCOMMIT;"
    try:
        conexion.executescript(guion)
    except sqlite3.Error as error:
        conexion.rollback()
        nombres = ", ".join(str(ruta.name if hasattr(ruta, "name") else ruta) for ruta in rutas)
        raise type(error)(f"{error} (al ejecutar: {nombres}; no se guardó ningún cambio)") from error


def crear_tablas(conexion):
    """Crea las tablas, índices y vistas (sql/esquema.sql)."""
    _ejecutar_como_una_sola_operacion(conexion, RUTA_ESQUEMA)


def cargar_datos(conexion):
    """Inserta los datos de ejemplo (sql/datos.sql)."""
    _ejecutar_como_una_sola_operacion(conexion, RUTA_DATOS)


def inicializar(conexion):
    """Crea las tablas y carga los datos de ejemplo como una sola operación."""
    _ejecutar_como_una_sola_operacion(conexion, RUTA_ESQUEMA, RUTA_DATOS)
