"""Modelo Empleado: personal que procesa los préstamos y devoluciones."""

from src.models.base import Modelo


class Empleado(Modelo):
    tabla = "empleado"
    pk = "id_empleado"
    campos = ("nombre", "apellido", "cargo", "usuario_sistema", "estado")

    def __init__(self, nombre, apellido, cargo, usuario_sistema,
                 estado="Activo", id_empleado=None):
        self.id_empleado = id_empleado
        self.nombre = nombre
        self.apellido = apellido
        self.cargo = cargo
        self.usuario_sistema = usuario_sistema
        self.estado = estado  # Activo o Inactivo
