"""Reportes: consultas de solo lectura sobre las vistas de la base de datos."""


def catalogo(conexion):
    """Cada material con su cantidad de ejemplares disponibles y prestados."""
    return conexion.execute("SELECT * FROM vista_catalogo ORDER BY titulo").fetchall()


def disponibilidad(conexion, solo_disponibles=False):
    """Estado de cada ejemplar (con opción de ver solo los disponibles)."""
    sql = "SELECT * FROM vista_disponibilidad"
    if solo_disponibles:
        sql += " WHERE estado = 'Disponible'"
    return conexion.execute(sql + " ORDER BY codigo").fetchall()


def prestamos_activos(conexion):
    """Préstamos que todavía no se han devuelto."""
    return conexion.execute(
        "SELECT * FROM vista_historial_prestamos "
        "WHERE fecha_devolucion IS NULL ORDER BY fecha_limite"
    ).fetchall()


def historial_usuario(conexion, documento):
    """Todos los préstamos de una persona, buscándola por su documento."""
    return conexion.execute(
        "SELECT * FROM vista_historial_prestamos WHERE documento = ? "
        "ORDER BY fecha_prestamo",
        (documento,),
    ).fetchall()


def historial_ejemplar(conexion, codigo):
    """Todos los préstamos de una copia física, buscándola por su código."""
    return conexion.execute(
        "SELECT * FROM vista_historial_prestamos WHERE codigo_ejemplar = ? "
        "ORDER BY fecha_prestamo",
        (codigo,),
    ).fetchall()
