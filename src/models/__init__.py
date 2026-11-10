"""Modelos (clases de la capa de datos). Una clase por cada tabla principal."""

from src.models.autor import Autor
from src.models.categoria import Categoria
from src.models.ejemplar import Ejemplar
from src.models.empleado import Empleado
from src.models.material import Material
from src.models.prestamo import ErrorPrestamo, Prestamo
from src.models.usuario import Usuario

__all__ = ["Autor", "Categoria", "Ejemplar", "Empleado", "Material",
           "Prestamo", "ErrorPrestamo", "Usuario"]
