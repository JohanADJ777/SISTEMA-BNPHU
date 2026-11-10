"""Modelo Prestamo: salida y devolución de un ejemplar.

Además del CRUD, incluye las dos reglas del negocio principales:
registrar() presta un ejemplar y devolver() lo recibe de vuelta.
"""

from datetime import date, timedelta

from src.config import DIAS_PRESTAMO
from src.models.base import Modelo
from src.models.ejemplar import Ejemplar
from src.models.empleado import Empleado
from src.models.usuario import Usuario


class ErrorPrestamo(Exception):
    """Se lanza cuando un préstamo o devolución no se puede realizar."""


class Prestamo(Modelo):
    tabla = "prestamo"
    pk = "id_prestamo"
    campos = ("id_usuario", "id_ejemplar", "id_empleado", "fecha_prestamo",
              "fecha_limite", "fecha_devolucion", "estado")

    def __init__(self, id_usuario, id_ejemplar, id_empleado, fecha_prestamo,
                 fecha_limite, fecha_devolucion=None, estado="Activo",
                 id_prestamo=None):
        self.id_prestamo = id_prestamo
        self.id_usuario = id_usuario
        self.id_ejemplar = id_ejemplar
        self.id_empleado = id_empleado
        self.fecha_prestamo = fecha_prestamo      # texto AAAA-MM-DD
        self.fecha_limite = fecha_limite
        self.fecha_devolucion = fecha_devolucion  # None mientras no se devuelva
        self.estado = estado                      # Activo, Atrasado o Devuelto

    # ---------- Regla: registrar un préstamo ----------
    @classmethod
    def registrar(cls, conexion, id_usuario, id_ejemplar, id_empleado,
                  dias=DIAS_PRESTAMO):
        usuario = Usuario.consultar(conexion, id_usuario)
        if usuario is None:
            raise ErrorPrestamo("El usuario no existe.")
        if usuario.estado != "Activo":
            raise ErrorPrestamo(f"El usuario está {usuario.estado.lower()} y no puede "
                                "pedir prestado.")

        if Empleado.consultar(conexion, id_empleado) is None:
            raise ErrorPrestamo("El empleado que registra el préstamo no existe.")

        ejemplar = Ejemplar.consultar(conexion, id_ejemplar)
        if ejemplar is None:
            raise ErrorPrestamo("El ejemplar no existe.")
        if ejemplar.estado != "Disponible":
            raise ErrorPrestamo(f"El ejemplar {ejemplar.codigo} no está disponible "
                                f"(estado: {ejemplar.estado}).")

        hoy = date.today()
        prestamo = cls(id_usuario, id_ejemplar, id_empleado,
                       hoy.isoformat(), (hoy + timedelta(days=dias)).isoformat())

        # Las dos escrituras se hacen juntas: o se guardan ambas o ninguna
        with conexion:
            cursor = conexion.execute(
                """INSERT INTO prestamo (id_usuario, id_ejemplar, id_empleado,
                                         fecha_prestamo, fecha_limite, estado)
                   VALUES (?, ?, ?, ?, ?, 'Activo')""",
                (id_usuario, id_ejemplar, id_empleado,
                 prestamo.fecha_prestamo, prestamo.fecha_limite),
            )
            conexion.execute(
                "UPDATE ejemplar SET estado = 'Prestado' WHERE id_ejemplar = ?",
                (id_ejemplar,),
            )
        prestamo.id_prestamo = cursor.lastrowid
        return prestamo

    # ---------- Regla: registrar una devolución ----------
    def devolver(self, conexion):
        if self.estado == "Devuelto" or self.fecha_devolucion:
            raise ErrorPrestamo("Este préstamo ya fue devuelto.")

        # la base exige que la devolución no sea anterior al préstamo
        fecha = max(date.today().isoformat(), self.fecha_prestamo)
        with conexion:
            conexion.execute(
                "UPDATE prestamo SET fecha_devolucion = ?, estado = 'Devuelto' "
                "WHERE id_prestamo = ?",
                (fecha, self.id_prestamo),
            )
            conexion.execute(
                "UPDATE ejemplar SET estado = 'Disponible' "
                "WHERE id_ejemplar = ? AND estado = 'Prestado'",
                (self.id_ejemplar,),
            )
        # el objeto solo cambia si la base de datos aceptó el cambio
        self.fecha_devolucion = fecha
        self.estado = "Devuelto"
        return self
