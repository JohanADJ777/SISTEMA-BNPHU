"""Consultas y cambios sobre la base de datos que usan las pantallas.

Las pantallas no escriben SQL: llaman a estas funciones. Los errores que la
persona debe leer se lanzan como ErrorDatos con un mensaje en español.
"""

import sqlite3
from datetime import date, timedelta

from src.config import DIAS_PRESTAMO
from src.interfaz import seguridad
from src.models import ErrorPrestamo, Prestamo


class ErrorDatos(Exception):
    """Dato inválido o regla del sistema que no se cumple."""


def hoy():
    return date.today().isoformat()


def _uno(con, sql, *params):
    return con.execute(sql, params).fetchone()[0]


# ----------------------------------------------------------------------
# Resumen del inicio
# ----------------------------------------------------------------------
def actualizar_atrasos(con):
    """Marca como 'Atrasado' los préstamos activos cuya fecha límite ya pasó."""
    con.execute("UPDATE prestamo SET estado = 'Atrasado' WHERE fecha_devolucion IS NULL "
                "AND estado = 'Activo' AND fecha_limite < ?", (hoy(),))
    con.commit()


def estadisticas(con):
    return {
        "usuarios": _uno(con, "SELECT COUNT(*) FROM usuario WHERE estado = 'Activo'"),
        "prestamos": _uno(con, "SELECT COUNT(*) FROM prestamo WHERE fecha_devolucion IS NULL"),
        "materiales": _uno(con, "SELECT COUNT(*) FROM material"),
        "atrasados": _uno(con, "SELECT COUNT(*) FROM prestamo WHERE fecha_devolucion IS NULL "
                               "AND fecha_limite < ?", hoy()),
        "autores": _uno(con, "SELECT COUNT(*) FROM autor"),
        "ejemplares": _uno(con, "SELECT COUNT(*) FROM ejemplar"),
        "disponibles": _uno(con, "SELECT COUNT(*) FROM ejemplar WHERE estado = 'Disponible'"),
    }


def populares(con, limite=6):
    return con.execute("""
        SELECT m.id_material, m.titulo, c.nombre AS categoria, COUNT(p.id_prestamo) AS veces
        FROM material m
        JOIN categoria c ON c.id_categoria = m.categoria_id
        LEFT JOIN ejemplar e ON e.id_material = m.id_material
        LEFT JOIN prestamo p ON p.id_ejemplar = e.id_ejemplar
        GROUP BY m.id_material ORDER BY veces DESC, m.titulo LIMIT ?""", (limite,)).fetchall()


def autores_destacados(con, limite=7):
    return con.execute("""
        SELECT a.id_autor, a.nombre || ' ' || a.apellido AS nombre, COUNT(p.id_prestamo) AS veces
        FROM autor a
        LEFT JOIN material_autor ma ON ma.id_autor = a.id_autor
        LEFT JOIN ejemplar e ON e.id_material = ma.id_material
        LEFT JOIN prestamo p ON p.id_ejemplar = e.id_ejemplar
        GROUP BY a.id_autor ORDER BY veces DESC, a.apellido LIMIT ?""", (limite,)).fetchall()


def por_vencer(con, limite=5, id_usuario=None):
    filtro, params = "", []
    if id_usuario:
        filtro, params = "AND p.id_usuario = ?", [id_usuario]
    return con.execute(f"""
        SELECT p.id_prestamo, m.titulo, p.fecha_limite, p.estado,
               u.nombre || ' ' || u.apellido AS usuario
        FROM prestamo p
        JOIN ejemplar e ON e.id_ejemplar = p.id_ejemplar
        JOIN material m ON m.id_material = e.id_material
        JOIN usuario u ON u.id_usuario = p.id_usuario
        WHERE p.fecha_devolucion IS NULL {filtro}
        ORDER BY p.fecha_limite LIMIT ?""", (*params, limite)).fetchall()


def atrasados_de(con, id_usuario=None):
    if id_usuario:
        return _uno(con, "SELECT COUNT(*) FROM prestamo WHERE fecha_devolucion IS NULL "
                         "AND fecha_limite < ? AND id_usuario = ?", hoy(), id_usuario)
    return _uno(con, "SELECT COUNT(*) FROM prestamo WHERE fecha_devolucion IS NULL "
                     "AND fecha_limite < ?", hoy())


def leidos_por(con, id_usuario):
    """(préstamos que ha hecho, préstamos activos ahora)."""
    total = _uno(con, "SELECT COUNT(*) FROM prestamo WHERE id_usuario = ?", id_usuario)
    activos = _uno(con, "SELECT COUNT(*) FROM prestamo WHERE id_usuario = ? "
                        "AND fecha_devolucion IS NULL", id_usuario)
    return total, activos


# ----------------------------------------------------------------------
# Usuarios (lectores)
# ----------------------------------------------------------------------
ESTADOS_USUARIO = ("Activo", "Inactivo", "Suspendido")


def listar_usuarios(con, texto=""):
    t = f"%{texto.strip()}%"
    return con.execute(
        "SELECT * FROM usuario WHERE nombre LIKE ? OR apellido LIKE ? OR documento LIKE ? "
        "OR correo LIKE ? ORDER BY apellido, nombre", (t, t, t, t)).fetchall()


def _validar_usuario(con, d, id_actual=None):
    for clave, etiqueta in (("nombre", "el nombre"), ("apellido", "el apellido"),
                            ("documento", "el documento")):
        if not d.get(clave, "").strip():
            raise ErrorDatos(f"Escribe {etiqueta}.")
    if d.get("correo") and ("@" not in d["correo"] or "." not in d["correo"].split("@")[-1]):
        raise ErrorDatos("El correo no parece válido (ejemplo: nombre@correo.com).")
    if d.get("telefono") and not all(c.isdigit() or c in "-+() " for c in d["telefono"]):
        raise ErrorDatos("El teléfono solo puede tener números y guiones.")
    if d.get("estado") not in ESTADOS_USUARIO:
        raise ErrorDatos("Elige el estado del usuario.")
    if d.get("correo"):
        otro = con.execute("SELECT 1 FROM usuario WHERE lower(correo) = lower(?) "
                           "AND id_usuario <> ?", (d["correo"], id_actual or 0)).fetchone()
        if otro:
            raise ErrorDatos("Ya existe un usuario con ese correo.")


def crear_usuario(con, d):
    """Crea el usuario y su cuenta de acceso. Devuelve (id_usuario, nombre_de_cuenta)."""
    _validar_usuario(con, d)
    try:
        with con:
            cur = con.execute(
                "INSERT INTO usuario (nombre, apellido, documento, telefono, correo, estado) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (d["nombre"], d["apellido"], d["documento"], d.get("telefono") or None,
                 d.get("correo") or None, d["estado"]))
    except sqlite3.IntegrityError:
        raise ErrorDatos("Ya existe un usuario con ese documento.")
    cuenta = seguridad.crear_cuenta_lector(con, cur.lastrowid, d["nombre"], d["apellido"],
                                           d.get("correo"))
    return cur.lastrowid, cuenta


def actualizar_usuario(con, id_usuario, d):
    _validar_usuario(con, d, id_usuario)
    try:
        with con:
            con.execute(
                "UPDATE usuario SET nombre=?, apellido=?, documento=?, telefono=?, correo=?, "
                "estado=? WHERE id_usuario=?",
                (d["nombre"], d["apellido"], d["documento"], d.get("telefono") or None,
                 d.get("correo") or None, d["estado"], id_usuario))
    except sqlite3.IntegrityError:
        raise ErrorDatos("Ya existe otro usuario con ese documento.")


def eliminar_usuario(con, id_usuario):
    try:
        with con:
            con.execute("DELETE FROM cuenta WHERE id_usuario = ?", (id_usuario,))
            con.execute("DELETE FROM usuario WHERE id_usuario = ?", (id_usuario,))
    except sqlite3.IntegrityError:
        raise ErrorDatos("No se puede eliminar: el usuario tiene préstamos registrados.\n"
                         "Cámbialo a «Inactivo» para conservar su historial.")


# ----------------------------------------------------------------------
# Materiales, autores y ejemplares
# ----------------------------------------------------------------------
def categorias(con):
    return con.execute("SELECT id_categoria, nombre FROM categoria ORDER BY nombre").fetchall()


def listar_materiales(con, texto=""):
    t = f"%{texto.strip()}%"
    return con.execute("""
        SELECT m.id_material, m.titulo, m.anio, m.isbn, m.categoria_id, c.nombre AS categoria,
               COALESCE((SELECT GROUP_CONCAT(a.nombre || ' ' || a.apellido, ', ')
                         FROM material_autor ma JOIN autor a ON a.id_autor = ma.id_autor
                         WHERE ma.id_material = m.id_material), '') AS autores,
               (SELECT COUNT(*) FROM ejemplar e WHERE e.id_material = m.id_material) AS ejemplares
        FROM material m JOIN categoria c ON c.id_categoria = m.categoria_id
        WHERE m.titulo LIKE ? OR m.isbn LIKE ? OR EXISTS (
              SELECT 1 FROM material_autor x JOIN autor y ON y.id_autor = x.id_autor
              WHERE x.id_material = m.id_material AND y.nombre || ' ' || y.apellido LIKE ?)
        ORDER BY m.titulo""", (t, t, t)).fetchall()


def _autor(con, nombre_completo):
    """Busca al autor por su nombre completo y, si no existe, lo crea."""
    partes = nombre_completo.split()
    fila = con.execute("SELECT id_autor FROM autor WHERE lower(nombre || ' ' || apellido) = lower(?)",
                       (" ".join(partes),)).fetchone()
    if fila:
        return fila[0]
    nombre, apellido = partes[0], " ".join(partes[1:]) or "-"
    return con.execute("INSERT INTO autor (nombre, apellido) VALUES (?, ?)",
                       (nombre, apellido)).lastrowid


def _guardar_autores(con, id_material, texto):
    con.execute("DELETE FROM material_autor WHERE id_material = ?", (id_material,))
    for nombre in {n.strip() for n in (texto or "").split(",") if n.strip()}:
        con.execute("INSERT OR IGNORE INTO material_autor (id_material, id_autor) VALUES (?, ?)",
                    (id_material, _autor(con, nombre)))


def _validar_material(d):
    if not d.get("titulo", "").strip():
        raise ErrorDatos("Escribe el título del material.")
    if not d.get("categoria_id"):
        raise ErrorDatos("Elige una categoría.")
    if d.get("anio"):
        if not str(d["anio"]).isdigit() or not 1000 <= int(d["anio"]) <= 2100:
            raise ErrorDatos("El año debe ser un número entre 1000 y 2100.")


def crear_material(con, d):
    _validar_material(d)
    try:
        with con:
            cur = con.execute(
                "INSERT INTO material (titulo, anio, isbn, categoria_id) VALUES (?, ?, ?, ?)",
                (d["titulo"], int(d["anio"]) if d.get("anio") else None,
                 d.get("isbn") or None, d["categoria_id"]))
            _guardar_autores(con, cur.lastrowid, d.get("autores"))
    except sqlite3.IntegrityError:
        raise ErrorDatos("Ya existe un material con ese ISBN.")
    return cur.lastrowid


def actualizar_material(con, id_material, d):
    _validar_material(d)
    try:
        with con:
            con.execute("UPDATE material SET titulo=?, anio=?, isbn=?, categoria_id=? "
                        "WHERE id_material=?",
                        (d["titulo"], int(d["anio"]) if d.get("anio") else None,
                         d.get("isbn") or None, d["categoria_id"], id_material))
            _guardar_autores(con, id_material, d.get("autores"))
    except sqlite3.IntegrityError:
        raise ErrorDatos("Ya existe otro material con ese ISBN.")


def eliminar_material(con, id_material):
    if _uno(con, "SELECT COUNT(*) FROM ejemplar WHERE id_material = ?", id_material):
        raise ErrorDatos("No se puede eliminar: el material tiene ejemplares registrados.")
    with con:
        con.execute("DELETE FROM material_autor WHERE id_material = ?", (id_material,))
        con.execute("DELETE FROM material WHERE id_material = ?", (id_material,))


def ejemplares_de(con, id_material):
    return con.execute("SELECT * FROM ejemplar WHERE id_material = ? ORDER BY codigo",
                       (id_material,)).fetchall()


def agregar_ejemplar(con, id_material):
    """Crea un ejemplar nuevo con el siguiente código BNPHU-###. Devuelve el código."""
    numeros = [int(c[0].split("-")[-1]) for c in con.execute("SELECT codigo FROM ejemplar")
               if c[0].startswith("BNPHU-") and c[0].split("-")[-1].isdigit()]
    codigo = f"BNPHU-{max(numeros, default=0) + 1:03d}"
    with con:
        con.execute("INSERT INTO ejemplar (id_material, codigo) VALUES (?, ?)",
                    (id_material, codigo))
    return codigo


# ----------------------------------------------------------------------
# Préstamos y devoluciones
# ----------------------------------------------------------------------
def usuarios_para_prestamo(con):
    return con.execute(
        "SELECT id_usuario, estado, apellido || ', ' || nombre || '  (' || documento || ')' "
        "AS etiqueta FROM usuario ORDER BY apellido, nombre").fetchall()


def ejemplares_disponibles(con, texto=""):
    t = f"%{texto.strip()}%"
    return con.execute("""
        SELECT e.id_ejemplar, e.codigo || '  -  ' || m.titulo AS etiqueta
        FROM ejemplar e JOIN material m ON m.id_material = e.id_material
        WHERE e.estado = 'Disponible' AND (m.titulo LIKE ? OR e.codigo LIKE ?)
        ORDER BY m.titulo, e.codigo""", (t, t)).fetchall()


def registrar_prestamo(con, id_usuario, id_ejemplar, id_empleado, dias=None):
    """Registra el préstamo y deja el ejemplar como 'Prestado'. Devuelve la fecha límite.

    Las reglas del negocio (usuario activo, ejemplar disponible, empleado que
    existe) viven en el modelo Prestamo: aquí solo se revisan los datos que
    llegan de la pantalla y se traducen los errores a mensajes para la persona.
    """
    if not id_usuario:
        raise ErrorDatos("Elige el usuario que se lleva el material.")
    if not id_ejemplar:
        raise ErrorDatos("Elige el ejemplar que se va a prestar.")
    if not id_empleado:
        raise ErrorDatos("Esta cuenta no está enlazada con ningún empleado de la biblioteca, "
                         "por eso no puede registrar préstamos.\n"
                         "Ejecuta reparar_base.py y vuelve a iniciar sesión.")
    if dias in (None, ""):
        dias = DIAS_PRESTAMO
    if not str(dias).isdigit() or not 1 <= int(dias) <= 60:
        raise ErrorDatos("Los días de préstamo deben ser un número entre 1 y 60.")
    try:
        prestamo = Prestamo.registrar(con, id_usuario, id_ejemplar, id_empleado, int(dias))
    except ErrorPrestamo as error:
        raise ErrorDatos(str(error)) from error
    except sqlite3.IntegrityError as error:
        raise ErrorDatos(f"La base de datos no aceptó el préstamo: {error}") from error
    return prestamo.fecha_limite


def prestamos_recientes(con, limite=8):
    return con.execute("SELECT * FROM vista_historial_prestamos ORDER BY id_prestamo DESC LIMIT ?",
                       (limite,)).fetchall()


def devolver_prestamo(con, id_prestamo):
    """Registra la devolución (regla del modelo Prestamo). Devuelve el préstamo."""
    prestamo = Prestamo.consultar(con, id_prestamo)
    if prestamo is None:
        raise ErrorDatos("No se encontró ese préstamo.")
    try:
        return prestamo.devolver(con)
    except ErrorPrestamo as error:
        raise ErrorDatos(str(error)) from error
