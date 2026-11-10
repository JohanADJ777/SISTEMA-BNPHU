"""Repara la base de datos bnphu.db SIN perder datos.

Cuándo usarlo: cuando la base se creó con un datos.sql que fallaba a la mitad
(por ejemplo, por una coma de más) y quedó sin empleados ni préstamos, con
ejemplares «Prestado» que no tienen préstamo, o con la cuenta admin sin empleado.

Qué hace (cada paso solo actúa si hace falta, así que se puede ejecutar varias veces):

  1. Guarda una copia de respaldo de tu base en la carpeta respaldo/.
  2. Si no hay empleados, carga los de datos.sql.
  3. Si no hay préstamos, carga los de datos.sql (solo si encajan con tus datos).
  4. Enlaza la cuenta admin con un empleado y crea las cuentas de los empleados.
  5. Enlaza el material «Cosmos» con su autor, Carl Sagan.
  6. Mueve a respaldo/ el archivo duplicado bnphu.db.db (no lo borra).
  7. Avisa si hay usuarios con el mismo correo (esos los decides tú).

Uso (desde la carpeta del proyecto, con DB Browser y SQLTools cerrados):

    python reparar_base.py
"""

import shutil
import sqlite3
import sys
from datetime import datetime

from src import database
from src.config import RAIZ, RUTA_BD
from src.interfaz import seguridad

CARPETA_RESPALDO = RAIZ / "respaldo"


def linea(texto=""):
    print(texto)


def respaldar():
    CARPETA_RESPALDO.mkdir(exist_ok=True)
    destino = CARPETA_RESPALDO / f"bnphu_respaldo_{datetime.now():%Y%m%d_%H%M%S}.db"
    origen = sqlite3.connect(str(RUTA_BD))
    copia = sqlite3.connect(str(destino))
    with copia:
        origen.backup(copia)
    origen.close()
    copia.close()
    return destino


def cargar_empleados(con, modelo):
    if con.execute("SELECT COUNT(*) FROM empleado").fetchone()[0]:
        linea("  - Empleados: ya hay empleados, no se toca nada.")
        return
    filas = modelo.execute("SELECT * FROM empleado ORDER BY id_empleado").fetchall()
    with con:
        for f in filas:
            con.execute("INSERT INTO empleado (id_empleado, nombre, apellido, cargo, "
                        "usuario_sistema, estado) VALUES (?, ?, ?, ?, ?, ?)",
                        (f["id_empleado"], f["nombre"], f["apellido"], f["cargo"],
                         f["usuario_sistema"], f["estado"]))
    linea(f"  - Empleados: se cargaron {len(filas)} empleados.")


def cargar_prestamos(con, modelo):
    if con.execute("SELECT COUNT(*) FROM prestamo").fetchone()[0]:
        linea("  - Préstamos: ya hay préstamos, no se toca nada.")
        return
    filas = modelo.execute("SELECT p.*, e.codigo FROM prestamo p "
                           "JOIN ejemplar e ON e.id_ejemplar = p.id_ejemplar "
                           "ORDER BY p.id_prestamo").fetchall()
    for f in filas:  # solo se cargan si encajan con los ejemplares y usuarios que ya existen
        mismo_ejemplar = con.execute("SELECT 1 FROM ejemplar WHERE id_ejemplar = ? AND codigo = ?",
                                     (f["id_ejemplar"], f["codigo"])).fetchone()
        usuario = con.execute("SELECT 1 FROM usuario WHERE id_usuario = ?",
                              (f["id_usuario"],)).fetchone()
        if not mismo_ejemplar or not usuario:
            linea("  - Préstamos: los ejemplares o usuarios de tu base no coinciden con "
                  "datos.sql; no se cargaron préstamos para no mezclar datos.")
            return
    with con:
        for f in filas:
            con.execute(
                "INSERT INTO prestamo (id_prestamo, id_usuario, id_ejemplar, id_empleado, "
                "fecha_prestamo, fecha_limite, fecha_devolucion, estado) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (f["id_prestamo"], f["id_usuario"], f["id_ejemplar"], f["id_empleado"],
                 f["fecha_prestamo"], f["fecha_limite"], f["fecha_devolucion"], f["estado"]))
            if f["fecha_devolucion"] is None:   # un préstamo abierto deja el ejemplar prestado
                con.execute("UPDATE ejemplar SET estado = 'Prestado' WHERE id_ejemplar = ?",
                            (f["id_ejemplar"],))
    linea(f"  - Préstamos: se cargaron {len(filas)} préstamos (y se enlazaron con sus ejemplares).")


def enlazar_cosmos(con):
    material = con.execute("SELECT id_material FROM material WHERE titulo = 'Cosmos'").fetchone()
    autor = con.execute("SELECT id_autor FROM autor WHERE nombre = 'Carl' AND apellido = 'Sagan'").fetchone()
    if not material or not autor:
        linea("  - Cosmos: no se encontró el material o el autor; no se toca nada.")
        return
    ya = con.execute("SELECT 1 FROM material_autor WHERE id_material = ?", (material[0],)).fetchone()
    if ya:
        linea("  - Cosmos: ya tiene autor.")
        return
    with con:
        con.execute("INSERT INTO material_autor (id_material, id_autor) VALUES (?, ?)",
                    (material[0], autor[0]))
    linea("  - Cosmos: se enlazó con su autor, Carl Sagan.")


def mover_duplicado():
    movidos = []
    for nombre in (RUTA_BD.name + ".db", RUTA_BD.name + ".db-journal"):
        ruta = RAIZ / nombre
        if ruta.exists():
            CARPETA_RESPALDO.mkdir(exist_ok=True)
            try:
                shutil.move(str(ruta), str(CARPETA_RESPALDO / nombre))
                movidos.append(nombre)
            except OSError as error:
                linea(f"  - Duplicado: no pude mover {nombre} ({error}). "
                      "Cierra DB Browser y vuelve a ejecutar este archivo.")
    if movidos:
        linea("  - Duplicado: se movió " + ", ".join(movidos) + " a la carpeta respaldo/ (no se borró).")
    else:
        linea("  - Duplicado: no hay un segundo archivo de base de datos.")


def avisar_repetidos(con):
    repetidos = con.execute(
        "SELECT lower(correo) AS c, COUNT(*) AS n FROM usuario WHERE correo IS NOT NULL "
        "AND correo <> '' GROUP BY lower(correo) HAVING COUNT(*) > 1").fetchall()
    if not repetidos:
        linea("  - Usuarios repetidos: no hay correos repetidos.")
        return
    for r in repetidos:
        linea(f"  - ATENCIÓN: el correo {r['c']} lo tienen {r['n']} usuarios:")
        for u in con.execute("SELECT id_usuario, nombre, apellido, documento, "
                             "(SELECT COUNT(*) FROM prestamo p WHERE p.id_usuario = u.id_usuario) AS prestamos "
                             "FROM usuario u WHERE lower(correo) = ? ORDER BY id_usuario", (r["c"],)):
            linea(f"      n.º {u['id_usuario']}: {u['nombre']} {u['apellido']} "
                  f"(documento {u['documento']}, {u['prestamos']} préstamos)")
        linea("    Si es la misma persona, elimina uno desde «Gestionar usuarios» "
              "(solo se puede si no tiene préstamos).")


def main():
    if not RUTA_BD.exists():
        linea(f"No existe {RUTA_BD}. Ejecuta python app.py una vez para crearla y vuelve a intentar.")
        return 1
    linea(f"Base de datos: {RUTA_BD}")
    try:
        respaldo = respaldar()
    except sqlite3.Error as error:
        linea(f"No pude abrir la base ({error}). Cierra DB Browser y SQLTools y vuelve a intentar.")
        return 1
    linea(f"1. Respaldo guardado en: {respaldo}")

    con = database.conectar()
    modelo = database.conectar(":memory:")      # base nueva y sana, solo para copiar datos de ejemplo
    try:
        database.inicializar(modelo)
        linea("2. Reparaciones:")
        try:
            cargar_empleados(con, modelo)
            cargar_prestamos(con, modelo)
            seguridad.preparar(con)
            linea("  - Cuentas: la cuenta admin queda enlazada con un empleado y cada empleado "
                  "tiene su cuenta.")
            enlazar_cosmos(con)
        except sqlite3.OperationalError as error:
            linea(f"  No pude escribir en la base ({error}). Cierra DB Browser y SQLTools y "
                  "vuelve a ejecutar este archivo.")
            return 1
        mover_duplicado()
        linea("3. Revisión:")
        avisar_repetidos(con)
        huerfanos = con.execute(
            "SELECT COUNT(*) FROM ejemplar e WHERE e.estado = 'Prestado' AND NOT EXISTS "
            "(SELECT 1 FROM prestamo p WHERE p.id_ejemplar = e.id_ejemplar "
            "AND p.fecha_devolucion IS NULL)").fetchone()[0]
        linea(f"  - Ejemplares «Prestado» sin préstamo: {huerfanos}")
        linea(f"  - integrity_check: {con.execute('PRAGMA integrity_check').fetchone()[0]}")
    finally:
        con.close()
        modelo.close()
    linea("\nListo. Ahora ejecuta:  python tests/lista_verificacion.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
