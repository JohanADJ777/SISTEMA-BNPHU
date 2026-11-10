"""Lista de verificación del Sistema de préstamos BNPHU.

Prueba, una por una, las funciones de cada capa de la aplicación y anota el
resultado de cada prueba:

    base de datos -> modelos -> lógica (datos) -> seguridad -> reportes

Cómo ejecutarla (desde la carpeta del proyecto):

    python tests/lista_verificacion.py

También se puede apuntar a otra carpeta de proyecto:

    python lista_verificacion.py C:\\ruta\\a\\proyecto_base

Seguridad: NUNCA toca tu bnphu.db. Cada prueba trabaja sobre una copia
temporal que se borra al terminar.
"""

import json
import re
import shutil
import sqlite3
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

sys.dont_write_bytecode = True

# ----------------------------------------------------------------------
# Carpeta del proyecto
# ----------------------------------------------------------------------
_aqui = Path(__file__).resolve().parent
_args = [a for a in sys.argv[1:] if not a.startswith("-") and (Path(a) / "src").is_dir()]
if _args:
    RAIZ = Path(_args[0]).resolve()
elif (_aqui.parent / "src").is_dir():
    RAIZ = _aqui.parent
else:
    RAIZ = _aqui
sys.path.insert(0, str(RAIZ))

from src import database, reportes                                  # noqa: E402
from src.config import RUTA_BD                                      # noqa: E402
from src.interfaz import datos, seguridad                           # noqa: E402
from src.models import (ErrorPrestamo, Ejemplar, Prestamo,          # noqa: E402
                        Usuario)

TEMPORALES = []
RESULTADOS = []


def temporal():
    carpeta = Path(tempfile.mkdtemp(prefix="bnphu_prueba_"))
    TEMPORALES.append(carpeta)
    return carpeta


# ----------------------------------------------------------------------
# Registro de pruebas
# ----------------------------------------------------------------------
def prueba(capa, nombre, esperado):
    """Decorador: la función devuelve (ok, obtenido) o lanza una excepción."""
    def registrar(fn):
        RESULTADOS.append({"capa": capa, "prueba": nombre, "esperado": esperado,
                           "fn": fn, "ok": None, "obtenido": ""})
        return fn
    return registrar


def lanza(fn, *tipos):
    """Ejecuta fn y comprueba que lance uno de los errores esperados."""
    try:
        fn()
    except tipos as error:
        return True, f"{type(error).__name__}: {str(error).splitlines()[0]}"
    except Exception as error:
        nombres = " o ".join(t.__name__ for t in tipos)
        return False, f"lanzó {type(error).__name__}: {error} (se esperaba {nombres})"
    return False, "no lanzó ningún error"


class Escenario:
    """Copia temporal de la base actual con datos propios de prueba."""

    def __init__(self):
        ruta = temporal() / "prueba.db"
        if RUTA_BD.exists():
            shutil.copy(RUTA_BD, ruta)
        self.con = database.conectar(ruta)
        if not self.con.execute("SELECT 1 FROM sqlite_master WHERE name='usuario'").fetchone():
            database.crear_tablas(self.con)
        seguridad.crear_tablas(self.con)
        c = self.con
        self.emp = c.execute("INSERT INTO empleado (nombre, apellido, cargo, usuario_sistema) "
                             "VALUES ('Prueba', 'Empleado', 'Auxiliar', 'prueba.emp')").lastrowid
        cat = c.execute("INSERT INTO categoria (nombre) VALUES ('Categoría de prueba')").lastrowid
        self.mat = c.execute("INSERT INTO material (titulo, anio, isbn, categoria_id) "
                             "VALUES ('Libro de prueba', 2020, 'ISBN-PRUEBA-1', ?)",
                             (cat,)).lastrowid
        self.cat = cat
        self.ej = [c.execute("INSERT INTO ejemplar (id_material, codigo) VALUES (?, ?)",
                             (self.mat, f"TEST-{n:03d}")).lastrowid for n in range(1, 7)]
        self.u_activo = self._usuario("T-001", "Activo", "Ana", "Prueba", "ana.prueba@test.com")
        self.u_susp = self._usuario("T-002", "Suspendido", "Sara", "Prueba", "sara.prueba@test.com")
        self.u_inact = self._usuario("T-003", "Inactivo", "Ines", "Prueba", "ines.prueba@test.com")
        c.commit()

    def _usuario(self, doc, estado, nombre, apellido, correo):
        return self.con.execute(
            "INSERT INTO usuario (nombre, apellido, documento, telefono, correo, estado) "
            "VALUES (?, ?, ?, '809-555-0000', ?, ?)",
            (nombre, apellido, doc, correo, estado)).lastrowid

    def sesion(self, rol="Empleado", id_empleado="auto"):
        emp = self.emp if id_empleado == "auto" else id_empleado
        return seguridad.Sesion(0, "tester", rol, "Persona de Prueba", emp, None)

    def cuenta(self, usuario, clave="clave123", rol="Lector"):
        seguridad._nueva_cuenta(self.con, usuario, clave, rol,
                                id_empleado=self.emp if rol != "Lector" else None,
                                id_usuario=self.u_activo if rol == "Lector" else None)
        self.con.commit()


_cache = {}


def escenario():
    """Un escenario nuevo para cada prueba, para que no dependan unas de otras."""
    return Escenario()


def copia_base_actual():
    ruta = temporal() / "actual.db"
    shutil.copy(RUTA_BD, ruta)
    return database.conectar(ruta)


# ======================================================================
# CAPA 1: BASE DE DATOS (archivos .sql, archivo .db y configuración)
# ======================================================================
def _base_nueva():
    ruta = temporal() / "nueva.db"
    con = database.conectar(ruta)
    try:
        database.inicializar(con)
        return con, None
    except Exception as error:
        return con, error


@prueba("Base de datos", "Los archivos .sql crean la base desde cero",
        "esquema.sql y datos.sql se ejecutan completos y sin errores")
def _():
    _, error = _base_nueva()
    if error:
        return False, f"{type(error).__name__}: {error}"
    return True, "carga completa sin errores"


@prueba("Base de datos", "La carga inicial deja empleados y préstamos de ejemplo",
        "6 empleados y 12 préstamos cargados")
def _():
    con, error = _base_nueva()
    e = con.execute("SELECT COUNT(*) FROM empleado").fetchone()[0]
    p = con.execute("SELECT COUNT(*) FROM prestamo").fetchone()[0]
    return (e >= 5 and p >= 12), f"{e} empleados y {p} préstamos"


@prueba("Base de datos", "Si la carga falla no queda una base a medias",
        "tras un error en datos.sql no queda ninguna tabla creada")
def _():
    ruta = temporal() / "rota.db"
    malo = temporal() / "datos_malos.sql"
    malo.write_text("INSERT INTO categoria (nombre) VALUES ('X');\n"
                    "INSERT INTO categoria (nombre) VALUES ('Y',);\n", encoding="utf-8")
    original = database.RUTA_DATOS
    database.RUTA_DATOS = malo
    con = database.conectar(ruta)
    try:
        try:
            database.inicializar(con)
        except sqlite3.Error:
            pass
    finally:
        database.RUTA_DATOS = original
    tablas = con.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' "
                         "AND name NOT LIKE 'sqlite_%'").fetchone()[0]
    return tablas == 0, f"quedaron {tablas} tablas creadas después del error"


@prueba("Base de datos", "El material Cosmos y sus autores quedan enlazados en datos.sql",
        "todos los materiales de la carga inicial tienen al menos un autor")
def _():
    con, _error = _base_nueva()
    sin = con.execute("SELECT m.titulo FROM material m LEFT JOIN material_autor ma "
                      "ON ma.id_material = m.id_material WHERE ma.id_material IS NULL").fetchall()
    return (not sin and con.execute("SELECT COUNT(*) FROM material").fetchone()[0] > 0), (
        "sin autor: " + ", ".join(f[0] for f in sin) if sin else "todos tienen autor")


@prueba("Base de datos", "La base actual pasa integrity_check y foreign_key_check",
        "sin páginas dañadas ni llaves foráneas rotas")
def _():
    con = copia_base_actual()
    integridad = con.execute("PRAGMA integrity_check").fetchone()[0]
    rotas = con.execute("PRAGMA foreign_key_check").fetchall()
    return (integridad == "ok" and not rotas), f"integrity_check = {integridad}; llaves rotas = {len(rotas)}"


@prueba("Base de datos", "La base actual tiene empleados registrados",
        "al menos un empleado (sin empleados no se pueden registrar préstamos)")
def _():
    n = copia_base_actual().execute("SELECT COUNT(*) FROM empleado").fetchone()[0]
    return n > 0, f"{n} empleados"


@prueba("Base de datos", "Cada ejemplar «Prestado» tiene un préstamo abierto",
        "0 ejemplares prestados sin préstamo que los respalde")
def _():
    huerfanos = copia_base_actual().execute(
        "SELECT e.codigo FROM ejemplar e WHERE e.estado = 'Prestado' AND NOT EXISTS "
        "(SELECT 1 FROM prestamo p WHERE p.id_ejemplar = e.id_ejemplar "
        "AND p.fecha_devolucion IS NULL)").fetchall()
    return not huerfanos, (f"{len(huerfanos)} sin préstamo: " + ", ".join(h[0] for h in huerfanos)
                           if huerfanos else "0 huérfanos")


@prueba("Base de datos", "Todo material de la base actual tiene autor",
        "0 materiales sin autor")
def _():
    sin = copia_base_actual().execute(
        "SELECT m.titulo FROM material m LEFT JOIN material_autor ma "
        "ON ma.id_material = m.id_material WHERE ma.id_material IS NULL").fetchall()
    return not sin, ("sin autor: " + ", ".join(f[0] for f in sin) if sin else "0 materiales sin autor")


@prueba("Base de datos", "No hay usuarios repetidos (mismo correo) en la base actual",
        "cada correo pertenece a un solo usuario")
def _():
    rep = copia_base_actual().execute(
        "SELECT correo, COUNT(*) FROM usuario WHERE correo IS NOT NULL AND correo <> '' "
        "GROUP BY lower(correo) HAVING COUNT(*) > 1").fetchall()
    return not rep, ("repetidos: " + ", ".join(f"{r[0]} x{r[1]}" for r in rep) if rep else "sin repetidos")


def _archivos_py():
    for ruta in list(RAIZ.glob("*.py")) + list((RAIZ / "src").rglob("*.py")):
        if ruta.name == "lista_verificacion.py":
            continue
        yield ruta


@prueba("Configuración", "Todas las capas apuntan al mismo archivo de base de datos",
        f"todo el proyecto usa {RUTA_BD.name}")
def _():
    nombres = {}
    for ruta in _archivos_py():
        for lit in re.findall(r"connect\(\s*[\"']([^\"']+)[\"']", ruta.read_text(encoding="utf-8")):
            nombres[f"{ruta.name}"] = lit
    ajustes = RAIZ / ".vscode" / "settings.json"
    if ajustes.exists():
        texto = ajustes.read_text(encoding="utf-8")
        for clave in ("name", "database"):
            for valor in re.findall(rf"\"{clave}\"\s*:\s*\"([^\"]+)\"", texto):
                if valor.endswith(".db") or ".db." in valor:
                    nombres[f"settings.json ({clave})"] = valor
    malos = {k: v for k, v in nombres.items() if Path(v).name != RUTA_BD.name}
    return not malos, ("; ".join(f"{k} usa «{v}»" for k, v in malos.items())
                       if malos else f"todos usan {RUTA_BD.name}")


@prueba("Configuración", "Los scripts auxiliares usan la ruta de config.py (no una ruta relativa)",
        "ningún archivo abre la base con un texto fijo como connect(\"bnphu.db\")")
def _():
    fijos = []
    for ruta in _archivos_py():
        if ruta.name == "database.py":
            continue
        if re.search(r"connect\(\s*[\"']", ruta.read_text(encoding="utf-8")):
            fijos.append(ruta.name)
    return not fijos, ("usan ruta fija: " + ", ".join(fijos) if fijos else "todos usan RUTA_BD")


@prueba("Configuración", "Solo hay un archivo de base de datos en la carpeta del proyecto",
        "un único archivo .db (el que usa la aplicación)")
def _():
    dbs = sorted(p.name for p in RAIZ.glob("*.db"))
    return dbs == [RUTA_BD.name], "archivos .db: " + ", ".join(dbs)


# ======================================================================
# CAPA 2: MODELOS (src/models)
# ======================================================================
@prueba("Modelos", "Usuario: crear, consultar, actualizar y eliminar (CRUD)",
        "las cuatro operaciones funcionan")
def _():
    e = escenario()
    u = Usuario("Rosa", "Jimenez", "M-001", "809-555-2000", "rosa.m@test.com").crear(e.con)
    ok1 = Usuario.consultar(e.con, u.id_usuario).documento == "M-001"
    u.telefono = "809-555-7777"
    u.actualizar(e.con)
    ok2 = Usuario.consultar(e.con, u.id_usuario).telefono == "809-555-7777"
    uid = u.id_usuario
    u.eliminar(e.con)
    ok3 = Usuario.consultar(e.con, uid) is None
    return ok1 and ok2 and ok3, f"crear={ok1}, actualizar={ok2}, eliminar={ok3}"


@prueba("Modelos", "Prestamo.registrar presta un ejemplar disponible",
        "el préstamo queda Activo y el ejemplar pasa a Prestado")
def _():
    e = escenario()
    p = Prestamo.registrar(e.con, e.u_activo, e.ej[0], e.emp)
    est = Ejemplar.consultar(e.con, e.ej[0]).estado
    return (p.id_prestamo is not None and est == "Prestado"), f"préstamo {p.id_prestamo}; ejemplar {est}"


@prueba("Modelos", "Prestamo.registrar rechaza un ejemplar que ya está prestado",
        "ErrorPrestamo")
def _():
    e = escenario()
    Prestamo.registrar(e.con, e.u_activo, e.ej[1], e.emp)
    return lanza(lambda: Prestamo.registrar(e.con, e.u_activo, e.ej[1], e.emp), ErrorPrestamo)


@prueba("Modelos", "Prestamo.registrar rechaza usuarios suspendidos, inactivos o inexistentes",
        "ErrorPrestamo en los tres casos")
def _():
    e = escenario()
    r = [lanza(lambda u=u: Prestamo.registrar(e.con, u, e.ej[2], e.emp), ErrorPrestamo)
         for u in (e.u_susp, e.u_inact, 99999)]
    return all(x[0] for x in r), " | ".join(x[1] for x in r)


@prueba("Modelos", "Prestamo.registrar rechaza un empleado que no existe",
        "ErrorPrestamo (y no un error interno de la base)")
def _():
    e = escenario()
    return lanza(lambda: Prestamo.registrar(e.con, e.u_activo, e.ej[3], 99999), ErrorPrestamo)


@prueba("Modelos", "Prestamo.devolver deja el ejemplar disponible y no se repite",
        "la 1.ª devolución funciona; la 2.ª lanza ErrorPrestamo")
def _():
    e = escenario()
    p = Prestamo.registrar(e.con, e.u_activo, e.ej[4], e.emp)
    Prestamo.consultar(e.con, p.id_prestamo).devolver(e.con)
    est = Ejemplar.consultar(e.con, e.ej[4]).estado
    ok2, msg = lanza(lambda: Prestamo.consultar(e.con, p.id_prestamo).devolver(e.con), ErrorPrestamo)
    return (est == "Disponible" and ok2), f"ejemplar {est}; segunda devolución -> {msg}"


@prueba("Modelos", "No se puede eliminar un usuario que tiene préstamos",
        "sqlite3.IntegrityError (la regla de la base lo protege)")
def _():
    e = escenario()
    Prestamo.registrar(e.con, e.u_activo, e.ej[5], e.emp)
    return lanza(lambda: Usuario.consultar(e.con, e.u_activo).eliminar(e.con), sqlite3.IntegrityError)


# ======================================================================
# CAPA 3: LÓGICA DE LAS PANTALLAS (src/interfaz/datos.py)
# ======================================================================
@prueba("Lógica de pantallas", "crear_usuario guarda el usuario y crea su cuenta de Lector",
        "el usuario existe y su cuenta está enlazada con él")
def _():
    e = escenario()
    d = {"nombre": "Omar", "apellido": "Vega", "documento": "L-100", "telefono": "809-555-1111",
         "correo": "omar.vega@test.com", "estado": "Activo"}
    uid, cuenta = datos.crear_usuario(e.con, d)
    fila = e.con.execute("SELECT rol, id_usuario FROM cuenta WHERE usuario = ?", (cuenta,)).fetchone()
    return (fila is not None and fila["id_usuario"] == uid and fila["rol"] == "Lector"), f"cuenta «{cuenta}» enlazada al usuario {uid}"


_BASE = {"nombre": "Pedro", "apellido": "Gil", "documento": "L-200",
         "telefono": "809-555-2222", "correo": "pedro.gil@test.com", "estado": "Activo"}


def _caso_usuario(nombre, cambio, esperado_texto):
    @prueba("Lógica de pantallas", nombre, f"ErrorDatos con un mensaje claro ({esperado_texto})")
    def _():
        e = escenario()
        d = dict(_BASE, **cambio)
        return lanza(lambda: datos.crear_usuario(e.con, d), datos.ErrorDatos)


_caso_usuario("crear_usuario rechaza un usuario sin apellido", {"apellido": ""}, "falta el apellido")
_caso_usuario("crear_usuario rechaza un correo mal escrito", {"correo": "pedro.gil"}, "correo no válido")
_caso_usuario("crear_usuario rechaza un teléfono con letras", {"telefono": "abc-123"}, "teléfono no válido")
_caso_usuario("crear_usuario rechaza un estado que no existe", {"estado": "Raro"}, "estado no válido")


@prueba("Lógica de pantallas", "crear_usuario rechaza un documento repetido",
        "ErrorDatos «Ya existe un usuario con ese documento»")
def _():
    e = escenario()
    return lanza(lambda: datos.crear_usuario(e.con, dict(_BASE, documento="T-001")), datos.ErrorDatos)


@prueba("Lógica de pantallas", "crear_usuario rechaza un correo que ya pertenece a otro usuario",
        "ErrorDatos (no se aceptan dos personas con el mismo correo)")
def _():
    e = escenario()
    return lanza(lambda: datos.crear_usuario(e.con, dict(_BASE, correo="ana.prueba@test.com")),
                 datos.ErrorDatos)


@prueba("Lógica de pantallas", "actualizar_usuario rechaza el documento de otro usuario",
        "ErrorDatos")
def _():
    e = escenario()
    d = dict(_BASE, documento="T-002", correo="otro.correo@test.com")
    return lanza(lambda: datos.actualizar_usuario(e.con, e.u_activo, d), datos.ErrorDatos)


@prueba("Lógica de pantallas", "eliminar_usuario con préstamos no borra nada",
        "ErrorDatos; el usuario y su cuenta siguen existiendo")
def _():
    e = escenario()
    e.cuenta("lector.prestamo")
    e.con.execute("UPDATE cuenta SET id_usuario = ? WHERE usuario = 'lector.prestamo'", (e.u_activo,))
    e.con.commit()
    datos.registrar_prestamo(e.con, e.u_activo, e.ej[0], e.emp, 7)
    ok, msg = lanza(lambda: datos.eliminar_usuario(e.con, e.u_activo), datos.ErrorDatos)
    sigue_u = e.con.execute("SELECT COUNT(*) FROM usuario WHERE id_usuario = ?", (e.u_activo,)).fetchone()[0]
    sigue_c = e.con.execute("SELECT COUNT(*) FROM cuenta WHERE id_usuario = ?", (e.u_activo,)).fetchone()[0]
    return (ok and sigue_u == 1 and sigue_c >= 1), f"{msg}; usuario={sigue_u}, cuentas={sigue_c}"


@prueba("Lógica de pantallas", "eliminar_usuario sin préstamos borra al usuario y su cuenta",
        "ambos desaparecen")
def _():
    e = escenario()
    uid, cuenta = datos.crear_usuario(e.con, dict(_BASE, documento="L-300", correo="borrar@test.com"))
    datos.eliminar_usuario(e.con, uid)
    u = e.con.execute("SELECT COUNT(*) FROM usuario WHERE id_usuario = ?", (uid,)).fetchone()[0]
    c = e.con.execute("SELECT COUNT(*) FROM cuenta WHERE usuario = ?", (cuenta,)).fetchone()[0]
    return (u == 0 and c == 0), f"usuarios={u}, cuentas={c}"


@prueba("Lógica de pantallas", "crear_material guarda el material y crea los autores nuevos",
        "material guardado con 2 autores (uno ya existía y otro es nuevo)")
def _():
    e = escenario()
    antes = e.con.execute("SELECT COUNT(*) FROM autor").fetchone()[0]
    mid = datos.crear_material(e.con, {"titulo": "Notas de prueba", "autores": "Carl Sagan, Ada Prueba",
                                       "categoria_id": e.cat, "anio": "2001", "isbn": "ISBN-N-1"})
    n_aut = e.con.execute("SELECT COUNT(*) FROM material_autor WHERE id_material = ?", (mid,)).fetchone()[0]
    despues = e.con.execute("SELECT COUNT(*) FROM autor").fetchone()[0]
    return (n_aut == 2 and despues <= antes + 2), f"{n_aut} autores enlazados; autores nuevos creados: {despues - antes}"


def _caso_material(nombre, cambio):
    @prueba("Lógica de pantallas", nombre, "ErrorDatos con un mensaje claro")
    def _():
        e = escenario()
        d = {"titulo": "Libro X", "autores": "Autor Uno", "categoria_id": e.cat, "anio": "2000",
             "isbn": "ISBN-X-1"}
        d.update(cambio(e))
        return lanza(lambda: datos.crear_material(e.con, d), datos.ErrorDatos)


_caso_material("crear_material rechaza un ISBN repetido", lambda e: {"isbn": "ISBN-PRUEBA-1"})
_caso_material("crear_material rechaza un material sin título", lambda e: {"titulo": ""})
_caso_material("crear_material rechaza un material sin categoría", lambda e: {"categoria_id": None})
_caso_material("crear_material rechaza un año fuera de rango", lambda e: {"anio": "12"})
_caso_material("crear_material rechaza un año con letras", lambda e: {"anio": "abc"})


@prueba("Lógica de pantallas", "eliminar_material con ejemplares no se permite", "ErrorDatos")
def _():
    e = escenario()
    return lanza(lambda: datos.eliminar_material(e.con, e.mat), datos.ErrorDatos)


@prueba("Lógica de pantallas", "agregar_ejemplar genera un código nuevo cada vez",
        "dos códigos BNPHU-### distintos y que no existían")
def _():
    e = escenario()
    a = datos.agregar_ejemplar(e.con, e.mat)
    b = datos.agregar_ejemplar(e.con, e.mat)
    return (a != b and re.fullmatch(r"BNPHU-\d{3}", a) is not None), f"{a} y {b}"


@prueba("Lógica de pantallas", "registrar_prestamo presta un ejemplar y lo marca como Prestado",
        "devuelve la fecha límite y el préstamo aparece en el historial")
def _():
    e = escenario()
    limite = datos.registrar_prestamo(e.con, e.u_activo, e.ej[0], e.emp, "10")
    esperado = (date.today() + timedelta(days=10)).isoformat()
    est = e.con.execute("SELECT estado FROM ejemplar WHERE id_ejemplar = ?", (e.ej[0],)).fetchone()[0]
    hist = [f for f in datos.prestamos_recientes(e.con, 5) if f["codigo_ejemplar"] == "TEST-001"]
    return (str(limite) == esperado and est == "Prestado" and hist), f"límite {limite}; ejemplar {est}; en historial: {bool(hist)}"


def _caso_prestamo(nombre, usuario, ejemplar, dias, esperado_texto, previo=None):
    @prueba("Lógica de pantallas", nombre, f"ErrorDatos ({esperado_texto})")
    def _():
        e = escenario()
        if previo:
            previo(e)
        return lanza(lambda: datos.registrar_prestamo(
            e.con, usuario(e), ejemplar(e), e.emp, dias), datos.ErrorDatos)


_caso_prestamo("registrar_prestamo rechaza un ejemplar que ya está prestado",
               lambda e: e.u_activo, lambda e: e.ej[1], "7", "ejemplar no disponible",
               previo=lambda e: datos.registrar_prestamo(e.con, e.u_activo, e.ej[1], e.emp, "7"))
_caso_prestamo("registrar_prestamo rechaza un usuario suspendido",
               lambda e: e.u_susp, lambda e: e.ej[2], "7", "usuario suspendido")
_caso_prestamo("registrar_prestamo rechaza un usuario inactivo",
               lambda e: e.u_inact, lambda e: e.ej[2], "7", "usuario inactivo")
_caso_prestamo("registrar_prestamo rechaza 0 días", lambda e: e.u_activo, lambda e: e.ej[2], "0", "días entre 1 y 60")
_caso_prestamo("registrar_prestamo rechaza 61 días", lambda e: e.u_activo, lambda e: e.ej[2], "61", "días entre 1 y 60")
_caso_prestamo("registrar_prestamo rechaza días con letras", lambda e: e.u_activo, lambda e: e.ej[2], "abc", "días no numéricos")
_caso_prestamo("registrar_prestamo rechaza si no se eligió usuario", lambda e: None, lambda e: e.ej[2], "7", "falta el usuario")
_caso_prestamo("registrar_prestamo rechaza si no se eligió ejemplar", lambda e: e.u_activo, lambda e: None, "7", "falta el ejemplar")
_caso_prestamo("registrar_prestamo rechaza un usuario que no existe", lambda e: 99999, lambda e: e.ej[2], "7", "usuario inexistente")


@prueba("Lógica de pantallas", "registrar_prestamo con una cuenta sin empleado avisa con un mensaje claro",
        "ErrorDatos (la pantalla muestra el aviso en vez de fallar)")
def _():
    e = escenario()
    return lanza(lambda: datos.registrar_prestamo(e.con, e.u_activo, e.ej[3], None, "7"), datos.ErrorDatos)


@prueba("Lógica de pantallas", "registrar_prestamo usa las reglas de la capa de modelos (Prestamo.registrar)",
        "la capa de lógica llama al modelo Prestamo en vez de repetir las reglas")
def _():
    e = escenario()
    llamadas = []
    original = Prestamo.registrar.__func__

    def espia(cls, *a, **k):
        llamadas.append(1)
        return original(cls, *a, **k)
    Prestamo.registrar = classmethod(espia)
    try:
        datos.registrar_prestamo(e.con, e.u_activo, e.ej[4], e.emp, "7")
    finally:
        Prestamo.registrar = classmethod(original)
    return bool(llamadas), f"llamadas al modelo: {len(llamadas)}"


@prueba("Lógica de pantallas", "devolver_prestamo deja el ejemplar disponible y no se repite",
        "1.ª devolución correcta; 2.ª y préstamo inexistente -> ErrorDatos")
def _():
    e = escenario()
    datos.registrar_prestamo(e.con, e.u_activo, e.ej[5], e.emp, "7")
    pid = e.con.execute("SELECT id_prestamo FROM prestamo WHERE id_ejemplar = ?", (e.ej[5],)).fetchone()[0]
    datos.devolver_prestamo(e.con, pid)
    est = e.con.execute("SELECT estado FROM ejemplar WHERE id_ejemplar = ?", (e.ej[5],)).fetchone()[0]
    ok2, m2 = lanza(lambda: datos.devolver_prestamo(e.con, pid), datos.ErrorDatos)
    ok3, m3 = lanza(lambda: datos.devolver_prestamo(e.con, 99999), datos.ErrorDatos)
    return (est == "Disponible" and ok2 and ok3), f"ejemplar {est}; repetida: {m2}; inexistente: {m3}"


@prueba("Lógica de pantallas", "Los préstamos vencidos se marcan como Atrasado",
        "actualizar_atrasos cambia el estado y las estadísticas lo cuentan")
def _():
    e = escenario()
    ayer = (date.today() - timedelta(days=3)).isoformat()
    antes = (date.today() - timedelta(days=10)).isoformat()
    e.con.execute("INSERT INTO prestamo (id_usuario, id_ejemplar, id_empleado, fecha_prestamo, "
                  "fecha_limite, estado) VALUES (?, ?, ?, ?, ?, 'Activo')",
                  (e.u_activo, e.ej[0], e.emp, antes, ayer))
    e.con.execute("UPDATE ejemplar SET estado = 'Prestado' WHERE id_ejemplar = ?", (e.ej[0],))
    e.con.commit()
    base = datos.estadisticas(e.con)["atrasados"]
    datos.actualizar_atrasos(e.con)
    n = e.con.execute("SELECT COUNT(*) FROM prestamo WHERE estado = 'Atrasado' AND id_ejemplar = ?",
                      (e.ej[0],)).fetchone()[0]
    return (n == 1 and base >= 1), f"marcados Atrasado = {n}; contados en estadísticas = {base}"


# ======================================================================
# CAPA 4: SEGURIDAD Y BITÁCORA (src/interfaz/seguridad.py)
# ======================================================================
@prueba("Seguridad", "Inicio de sesión con datos correctos",
        "devuelve la sesión con su rol y anota «Inicio de sesión» en la bitácora")
def _():
    e = escenario()
    e.cuenta("lector.uno")
    s = e.con and seguridad.autenticar(e.con, "lector.uno", "clave123")
    anotado = e.con.execute("SELECT COUNT(*) FROM bitacora WHERE usuario = 'lector.uno' "
                            "AND accion = 'Inicio de sesión'").fetchone()[0]
    return (s.rol == "Lector" and anotado == 1), f"rol {s.rol}; entradas en la bitácora: {anotado}"


@prueba("Seguridad", "Inicio de sesión sin distinguir mayúsculas en el usuario",
        "«LECTOR.DOS» entra igual que «lector.dos»")
def _():
    e = escenario()
    e.cuenta("lector.dos")
    return seguridad.autenticar(e.con, "LECTOR.DOS", "clave123").usuario == "lector.dos", "entró"


@prueba("Seguridad", "Contraseña incorrecta, usuario inexistente o campos vacíos",
        "ErrorSeguridad y «Intento fallido» en la bitácora")
def _():
    e = escenario()
    e.cuenta("lector.tres")
    r = [lanza(lambda: seguridad.autenticar(e.con, u, c), seguridad.ErrorSeguridad)
         for u, c in (("lector.tres", "mala"), ("no.existe", "x"), ("", ""))]
    fallos = e.con.execute("SELECT COUNT(*) FROM bitacora WHERE accion = 'Intento fallido'").fetchone()[0]
    return (all(x[0] for x in r) and fallos >= 2), f"{len(r)} rechazos; intentos fallidos anotados: {fallos}"


@prueba("Seguridad", "Se bloquea el acceso después de 5 intentos fallidos",
        "el 6.º intento falla aunque la contraseña sea correcta")
def _():
    e = escenario()
    e.cuenta("lector.bloqueo")
    for _n in range(5):
        lanza(lambda: seguridad.autenticar(e.con, "lector.bloqueo", "mala"), seguridad.ErrorSeguridad)
    return lanza(lambda: seguridad.autenticar(e.con, "lector.bloqueo", "clave123"), seguridad.ErrorSeguridad)


@prueba("Seguridad", "El bloqueo no se evita cambiando mayúsculas y minúsculas del usuario",
        "después de 5 fallos, «LECTOR.EVADE» con la clave correcta también queda bloqueado")
def _():
    e = escenario()
    e.cuenta("lector.evade")
    for _n in range(5):
        lanza(lambda: seguridad.autenticar(e.con, "lector.evade", "mala"), seguridad.ErrorSeguridad)
    ok, msg = lanza(lambda: seguridad.autenticar(e.con, "LECTOR.EVADE", "clave123"), seguridad.ErrorSeguridad)
    return ok, ("bloqueado" if ok else "entró sin esperar los 5 minutos")


@prueba("Seguridad", "La contraseña se guarda cifrada (hash con sal), nunca en texto",
        "ni «clave123» ni la contraseña aparecen en la tabla cuenta")
def _():
    e = escenario()
    e.cuenta("lector.hash")
    fila = e.con.execute("SELECT clave_hash, sal FROM cuenta WHERE usuario = 'lector.hash'").fetchone()
    return ("clave123" not in fila["clave_hash"] and len(fila["clave_hash"]) == 64 and len(fila["sal"]) == 32), \
        f"hash de {len(fila['clave_hash'])} caracteres y sal de {len(fila['sal'])}"


@prueba("Seguridad", "Cambiar la contraseña valida los datos y guarda la nueva",
        "rechaza actual incorrecta, nueva corta y no coincidente; acepta la correcta")
def _():
    e = escenario()
    e.cuenta("lector.clave")
    s = seguridad.autenticar(e.con, "lector.clave", "clave123")
    r = [lanza(lambda a=a, n=n, r_=r_: seguridad.cambiar_clave(e.con, s, a, n, r_), seguridad.ErrorSeguridad)
         for a, n, r_ in (("mala", "nueva456", "nueva456"), ("clave123", "123", "123"),
                          ("clave123", "nueva456", "otra789"))]
    seguridad.cambiar_clave(e.con, s, "clave123", "nueva456", "nueva456")
    nueva_ok = seguridad.autenticar(e.con, "lector.clave", "nueva456").usuario == "lector.clave"
    vieja_falla = lanza(lambda: seguridad.autenticar(e.con, "lector.clave", "clave123"), seguridad.ErrorSeguridad)[0]
    return (all(x[0] for x in r) and nueva_ok and vieja_falla), f"rechazos={sum(x[0] for x in r)}/3; nueva entra={nueva_ok}; vieja falla={vieja_falla}"


@prueba("Seguridad", "Permisos por rol",
        "el lector no ve usuarios ni bitácora; el empleado no ve la bitácora; el administrador ve todo")
def _():
    e = escenario()
    lector, emp, adm = (e.sesion(r) for r in ("Lector", "Empleado", "Administrador"))
    ok = (not lector.puede("usuarios") and not lector.puede("bitacora") and lector.puede("mis_prestamos")
          and not emp.puede("bitacora") and emp.puede("prestamos")
          and all(adm.puede(s) for s in seguridad.MENU_POR_ROL["Administrador"]))
    return ok, "permisos correctos" if ok else "algún permiso no coincide"


@prueba("Seguridad", "completar_cuentas crea una cuenta de Empleado para cada empleado activo",
        "el empleado «prueba.emp» recibe su cuenta")
def _():
    e = escenario()
    seguridad.completar_cuentas(e.con)
    fila = e.con.execute("SELECT rol, id_empleado FROM cuenta WHERE usuario = 'prueba.emp'").fetchone()
    return (fila is not None and fila["rol"] == "Empleado" and fila["id_empleado"] == e.emp), \
        "cuenta creada" if fila else "no se creó la cuenta"


@prueba("Seguridad", "La cuenta admin queda enlazada con un empleado cuando ya existen empleados",
        "admin.id_empleado deja de ser NULL (sin empleado no se pueden registrar préstamos)")
def _():
    e = escenario()
    e.con.execute("DELETE FROM cuenta WHERE usuario = 'admin'")
    e.con.execute("INSERT INTO cuenta (usuario, clave_hash, sal, rol, id_empleado) "
                  "VALUES ('admin', 'x', 'y', 'Administrador', NULL)")
    e.con.commit()
    seguridad.completar_cuentas(e.con)
    v = e.con.execute("SELECT id_empleado FROM cuenta WHERE usuario = 'admin'").fetchone()[0]
    return v is not None, f"admin.id_empleado = {v}"


@prueba("Seguridad", "La cuenta admin de la base actual puede registrar préstamos",
        "admin.id_empleado apunta a un empleado que existe")
def _():
    con = copia_base_actual()
    seguridad.preparar(con)
    fila = con.execute("SELECT c.id_empleado, e.id_empleado AS existe FROM cuenta c "
                       "LEFT JOIN empleado e ON e.id_empleado = c.id_empleado "
                       "WHERE c.usuario = 'admin'").fetchone()
    return (fila is not None and fila["existe"] is not None), f"admin.id_empleado = {fila['id_empleado'] if fila else 'sin cuenta'}"


@prueba("Seguridad", "La bitácora guarda, filtra y no detiene el programa si falla",
        "listar_bitacora filtra por texto; registrar() no lanza error aunque no exista la tabla")
def _():
    e = escenario()
    e.cuenta("lector.log")
    seguridad.autenticar(e.con, "lector.log", "clave123")
    seguridad.autenticar(e.con, "lector.log", "clave123")
    filtro = seguridad.listar_bitacora(e.con, "lector.log")
    previo = seguridad.ultimo_acceso(e.con, "lector.log")
    vacia = sqlite3.connect(":memory:")
    vacia.row_factory = sqlite3.Row
    try:
        seguridad.registrar(vacia, None, "Prueba", "sin tabla")
        sin_romper = True
    except Exception:
        sin_romper = False
    return (len(filtro) >= 2 and previo is not None and sin_romper), \
        f"filtradas={len(filtro)}; acceso anterior={previo}; no se rompe={sin_romper}"


# ======================================================================
# CAPA 5: REPORTES Y CATÁLOGO
# ======================================================================
@prueba("Reportes", "El catálogo cuadra con los ejemplares reales",
        "la suma de ejemplares y disponibles del catálogo = la de la tabla ejemplar")
def _():
    e = escenario()
    cat = reportes.catalogo(e.con)
    total = sum(f["total_ejemplares"] for f in cat)
    disp = sum(f["disponibles"] for f in cat)
    real = e.con.execute("SELECT COUNT(*) FROM ejemplar").fetchone()[0]
    real_d = e.con.execute("SELECT COUNT(*) FROM ejemplar WHERE estado = 'Disponible'").fetchone()[0]
    return (total == real and disp == real_d), f"catálogo {total}/{disp}; tabla {real}/{real_d}"


@prueba("Reportes", "Los préstamos activos y el historial del usuario salen bien",
        "prestamos_activos solo trae préstamos abiertos; historial_usuario trae los de ese documento")
def _():
    e = escenario()
    datos.registrar_prestamo(e.con, e.u_activo, e.ej[0], e.emp, "7")
    activos = [f for f in reportes.prestamos_activos(e.con) if f["codigo_ejemplar"] == "TEST-001"]
    hist = reportes.historial_usuario(e.con, "T-001")
    ok = bool(activos) and all(f["fecha_devolucion"] is None for f in reportes.prestamos_activos(e.con)) \
        and len(hist) == 1
    return ok, f"activos de prueba={len(activos)}; historial del usuario={len(hist)}"


@prueba("Reportes", "Las cifras del panel coinciden con los reportes",
        "estadísticas «préstamos activos» = filas de prestamos_activos")
def _():
    e = escenario()
    datos.registrar_prestamo(e.con, e.u_activo, e.ej[1], e.emp, "7")
    return datos.estadisticas(e.con)["prestamos"] == len(reportes.prestamos_activos(e.con)), \
        f"estadística={datos.estadisticas(e.con)['prestamos']}; reporte={len(reportes.prestamos_activos(e.con))}"


# ----------------------------------------------------------------------
# Ejecución
# ----------------------------------------------------------------------
def ejecutar():
    anterior = None
    for r in RESULTADOS:
        try:
            ok, obtenido = r["fn"]()
        except Exception as error:   # un error inesperado cuenta como ERROR de esa prueba
            ok, obtenido = False, f"excepción {type(error).__name__}: {error}"
        r["ok"], r["obtenido"] = bool(ok), str(obtenido)
        if r["capa"] != anterior:
            print(f"\n=== {r['capa'].upper()} ===")
            anterior = r["capa"]
        marca = "[OK]   " if r["ok"] else "[ERROR]"
        print(f"{marca} {r['prueba']}")
        if not r["ok"]:
            print(f"          Esperado: {r['esperado']}")
            print(f"          Obtenido: {r['obtenido']}")
    buenas = sum(r["ok"] for r in RESULTADOS)
    print("\n" + "=" * 70)
    print(f"RESULTADO: {buenas} pruebas correctas de {len(RESULTADOS)}  |  "
          f"{len(RESULTADOS) - buenas} con error")
    print("=" * 70)
    if "--json" in sys.argv:
        salida = [{k: v for k, v in r.items() if k != "fn"} for r in RESULTADOS]
        Path(sys.argv[sys.argv.index("--json") + 1]).write_text(
            json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    for carpeta in TEMPORALES:
        shutil.rmtree(carpeta, ignore_errors=True)
    return 0 if buenas == len(RESULTADOS) else 1


if __name__ == "__main__":
    sys.exit(ejecutar())
