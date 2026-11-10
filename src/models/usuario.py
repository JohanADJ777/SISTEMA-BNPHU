"""Modelo Usuario: persona que utiliza el servicio de préstamo."""

from src.models.base import Modelo


class Usuario(Modelo):
    tabla = "usuario"
    pk = "id_usuario"
    campos = ("nombre", "apellido", "documento", "telefono", "correo", "estado")

    def __init__(self, nombre, apellido, documento, telefono=None,
                 correo=None, estado="Activo", id_usuario=None):
        self.id_usuario = id_usuario
        self.nombre = nombre
        self.apellido = apellido
        self.documento = documento
        self.telefono = telefono
        self.correo = correo
        self.estado = estado  # Activo, Inactivo o Suspendido

    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}"
