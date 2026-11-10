"""Modelo Autor: persona que escribió uno o varios materiales."""

from src.models.base import Modelo


class Autor(Modelo):
    tabla = "autor"
    pk = "id_autor"
    campos = ("nombre", "apellido")

    def __init__(self, nombre, apellido, id_autor=None):
        self.id_autor = id_autor
        self.nombre = nombre
        self.apellido = apellido
