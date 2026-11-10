"""Punto de entrada: conecta con la base de datos y prueba el CRUD.

Para ejecutarlo:  python main.py
"""

import os
import sqlite3

from src.config import NOMBRE_PROYECTO, RUTA_BD, VERSION
from src.database import conectar, inicializar
from src.models import (Autor, Categoria, Ejemplar, Empleado, ErrorPrestamo,
                        Material, Prestamo, Usuario)
from src import reportes

TABLAS = ["categoria", "usuario", "empleado", "autor", "material",
          "material_autor", "ejemplar", "prestamo"]


def titulo(texto):
    print(f"\n{'=' * 60}\n{texto}\n{'=' * 60}")


def tabla(filas, columnas):
    """Imprime filas de la base de datos como una tabla sencilla."""
    if not filas:
        print("  (sin resultados)")
        return
    anchos = [max(len(c), *(len(str(f[c])) for f in filas)) for c in columnas]
    print("  " + " | ".join(c.ljust(a) for c, a in zip(columnas, anchos)))
    print("  " + "-+-".join("-" * a for a in anchos))
    for f in filas:
        print("  " + " | ".join(str(f[c]).ljust(a) for c, a in zip(columnas, anchos)))


def main():
    print(f"{NOMBRE_PROYECTO} v{VERSION}")

    # ------------------------------------------------------------------
    # 1. CONEXIÓN
    # ------------------------------------------------------------------
    titulo("1. CONEXIÓN CON LA BASE DE DATOS")
    if os.path.exists(RUTA_BD):   # empezamos limpios para que la prueba se repita
        os.remove(RUTA_BD)
    conexion = conectar()
    inicializar(conexion)
    print(f"Conexión exitosa a: {RUTA_BD.name}")
    print(f"Versión de SQLite: {sqlite3.sqlite_version}")
    print("Registros por tabla:")
    for t in TABLAS:
        total = conexion.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t:<15} {total}")

    # ------------------------------------------------------------------
    # 2. CRUD con la clase Usuario
    # ------------------------------------------------------------------
    titulo("2. CRUD - CREAR (clase Usuario)")
    nuevo = Usuario("Rosa", "Jimenez", "001-0000099-9", "809-555-2000",
                    "rosa.jimenez@example.com").crear(conexion)
    print("Usuario creado:", nuevo)

    titulo("3. CRUD - CONSULTAR")
    print("Por id:", Usuario.consultar(conexion, nuevo.id_usuario))
    print("Total de usuarios:", len(Usuario.listar(conexion)))
    print("Primeros 3 usuarios:")
    for u in Usuario.listar(conexion)[:3]:
        print("  ", u)

    titulo("4. CRUD - ACTUALIZAR")
    nuevo.telefono = "809-555-7777"
    nuevo.estado = "Suspendido"
    nuevo.actualizar(conexion)
    print("Después de actualizar:", Usuario.consultar(conexion, nuevo.id_usuario))

    titulo("5. CRUD - ELIMINAR")
    id_borrado = nuevo.id_usuario
    nuevo.eliminar(conexion)
    print(f"Usuario {id_borrado} eliminado. Al consultarlo:",
          Usuario.consultar(conexion, id_borrado))

    # Prueba de una regla de integridad: no se borra lo que tiene préstamos
    try:
        Usuario.consultar(conexion, 1).eliminar(conexion)
    except sqlite3.IntegrityError as error:
        print("Intentar borrar al usuario 1 (tiene préstamos) falla:", error)

    # ------------------------------------------------------------------
    # 3. CRUD con otras clases
    # ------------------------------------------------------------------
    titulo("6. CRUD - OTRAS CLASES (Categoria, Autor, Material, Ejemplar)")
    cat = Categoria("Pruebas", "Categoría temporal").crear(conexion)
    aut = Autor("Autor", "De Prueba").crear(conexion)
    mat = Material("Libro de prueba", cat.id_categoria, 2026, "9780000009999").crear(conexion)
    mat.agregar_autor(conexion, aut.id_autor)
    eje = Ejemplar(mat.id_material, "BNPHU-999").crear(conexion)
    print("Creados:", cat, aut, mat, eje, sep="\n  ")
    print("Autores del material:", mat.autores(conexion))
    mat.titulo = "Libro de prueba (2da edición)"
    mat.actualizar(conexion)
    print("Material actualizado:", Material.consultar(conexion, mat.id_material))
    eje.eliminar(conexion)
    conexion.execute("DELETE FROM material_autor WHERE id_material = ?", (mat.id_material,))
    mat.eliminar(conexion)
    aut.eliminar(conexion)
    cat.eliminar(conexion)
    print("Registros de prueba eliminados.")

    # ------------------------------------------------------------------
    # 4. PRÉSTAMO Y DEVOLUCIÓN
    # ------------------------------------------------------------------
    titulo("7. PRÉSTAMO Y DEVOLUCIÓN")
    libro = Material.buscar_por_titulo(conexion, "Historia Dominicana")[0]
    libres = Ejemplar.disponibles_de(conexion, libro.id_material)
    print(f"'{libro.titulo}': {len(libres)} ejemplares disponibles ->",
          [e.codigo for e in libres])

    prestamo = Prestamo.registrar(conexion, id_usuario=10,
                                  id_ejemplar=libres[0].id_ejemplar, id_empleado=1)
    print("Préstamo registrado:", prestamo)
    print("Estado del ejemplar ahora:",
          Ejemplar.consultar(conexion, libres[0].id_ejemplar).estado)

    try:
        Prestamo.registrar(conexion, 10, libres[0].id_ejemplar, 1)
    except ErrorPrestamo as error:
        print("Prestarlo otra vez no se permite:", error)
    try:
        Prestamo.registrar(conexion, 9, libres[1].id_ejemplar, 1)  # usuario suspendido
    except ErrorPrestamo as error:
        print("Usuario suspendido no puede pedir prestado:", error)

    prestamo.devolver(conexion)
    print("Devolución registrada:", prestamo.estado, prestamo.fecha_devolucion)
    print("Estado del ejemplar ahora:",
          Ejemplar.consultar(conexion, libres[0].id_ejemplar).estado)

    # ------------------------------------------------------------------
    # 5. REPORTES
    # ------------------------------------------------------------------
    titulo("8. REPORTES")
    print("Catálogo (disponibilidad por título):")
    tabla(reportes.catalogo(conexion)[:6],
          ["titulo", "categoria", "total_ejemplares", "disponibles", "prestados"])
    print("\nPréstamos activos:")
    tabla(reportes.prestamos_activos(conexion),
          ["id_prestamo", "usuario", "codigo_ejemplar", "titulo", "fecha_limite", "estado"])
    print("\nHistorial del usuario con documento 001-0000000-0:")
    tabla(reportes.historial_usuario(conexion, "001-0000000-0"),
          ["id_prestamo", "titulo", "fecha_prestamo", "fecha_devolucion", "estado"])

    conexion.close()
    print("\nPrueba terminada: conexión, CRUD, préstamos y reportes funcionan.")


if __name__ == "__main__":
    main()
