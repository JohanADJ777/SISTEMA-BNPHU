"""Cuentas de acceso, permisos y bitácora del sistema.

Todo lo que hace una persona dentro del programa (entrar, salir, abrir una
pantalla, guardar, borrar, equivocarse de contraseña...) se guarda en la tabla
`bitacora` de bnphu.db. Las contraseñas nunca se guardan en texto: se guarda
un hash PBKDF2 con una sal distinta para cada cuenta.
"""

import getpass
import hashlib
import hmac
import secrets
import socket
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta

ITERACIONES = 120_000
MAX_INTENTOS = 5          # intentos fallidos seguidos antes de bloquear
MINUTOS_BLOQUEO = 5

CLAVE_ADMIN = "admin123"
CLAVE_EMPLEADO = "empleado123"
CLAVE_LECTOR = "lector123"

ROLES = ("Administrador", "Empleado", "Lector")

# Secciones del menú que puede ver cada rol, en el orden en que se muestran.
MENU_POR_ROL = {
    "Administrador": ["inicio", "perfil", "usuarios", "materiales", "catalogo",
                      "prestamos", "devoluciones", "bitacora"],
    "Empleado": ["inicio", "perfil", "usuarios", "materiales", "catalogo",
                 "prestamos", "devoluciones"],
    "Lector": ["inicio", "catalogo", "mis_prestamos", "perfil"],
}


class ErrorSeguridad(Exception):
    """Problema al entrar o al cambiar la contraseña (el mensaje se muestra tal cual)."""


@dataclass
class Sesion:
    id_cuenta: int
    usuario: str
    rol: str
    nombre: str
    id_empleado: int = None
    id_usuario: int = None

    @property
    def es_personal(self):
        return self.rol in ("Administrador", "Empleado")

    @property
    def mostrar(self):
        """Nombre que se ve en pantalla (el usuario para el personal, como en el prototipo)."""
        return self.usuario if self.es_personal else self.nombre

    def puede(self, seccion):
        return seccion in MENU_POR_ROL[self.rol]


# ----------------------------------------------------------------------
# Tablas
# ----------------------------------------------------------------------
def crear_tablas(con):
    con.executescript("""
    CREATE TABLE IF NOT EXISTS cuenta (
        id_cuenta   INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario     TEXT NOT NULL UNIQUE,
        clave_hash  TEXT NOT NULL,
        sal         TEXT NOT NULL,
        rol         TEXT NOT NULL CHECK (rol IN ('Administrador', 'Empleado', 'Lector')),
        id_empleado INTEGER,
        id_usuario  INTEGER,
        activa      INTEGER NOT NULL DEFAULT 1,
        FOREIGN KEY (id_empleado) REFERENCES empleado (id_empleado),
        FOREIGN KEY (id_usuario)  REFERENCES usuario (id_usuario)
    );
    CREATE TABLE IF NOT EXISTS bitacora (
        id_bitacora INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha_hora  TEXT NOT NULL,
        usuario     TEXT,
        rol         TEXT,
        accion      TEXT NOT NULL,
        detalle     TEXT,
        equipo      TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_bitacora_fecha ON bitacora (fecha_hora);
    """)
    con.commit()


def _hash(clave, sal):
    return hashlib.pbkdf2_hmac("sha256", clave.encode("utf-8"),
                               bytes.fromhex(sal), ITERACIONES).hex()


def _nueva_cuenta(con, usuario, clave, rol, id_empleado=None, id_usuario=None):
    sal = secrets.token_hex(16)
    cur = con.execute(
        "INSERT INTO cuenta (usuario, clave_hash, sal, rol, id_empleado, id_usuario) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (usuario, _hash(clave, sal), sal, rol, id_empleado, id_usuario))
    return cur.lastrowid


def _sin_acentos(texto):
    base = unicodedata.normalize("NFD", texto)
    return "".join(c for c in base if unicodedata.category(c) != "Mn")


def nombre_de_cuenta_para(con, nombre, apellido, correo):
    """Propone un usuario libre: la parte del correo antes de @, o nombre.apellido."""
    base = (correo or "").split("@")[0] or f"{nombre}.{apellido}"
    base = _sin_acentos(base).lower().replace(" ", "")
    candidato, n = base, 1
    while con.execute("SELECT 1 FROM cuenta WHERE usuario = ?", (candidato,)).fetchone():
        n += 1
        candidato = f"{base}{n}"
    return candidato


def crear_cuenta_lector(con, id_usuario, nombre, apellido, correo):
    """Crea la cuenta de un lector nuevo y devuelve el nombre de usuario."""
    usuario = nombre_de_cuenta_para(con, nombre, apellido, correo)
    _nueva_cuenta(con, usuario, CLAVE_LECTOR, "Lector", id_usuario=id_usuario)
    con.commit()
    return usuario


def _empleado_para_admin(con):
    """Empleado al que se enlaza la cuenta admin (el administrador, o el primero activo)."""
    fila = con.execute(
        "SELECT id_empleado FROM empleado WHERE estado = 'Activo' "
        "ORDER BY (cargo LIKE '%dministrador%') DESC, id_empleado LIMIT 1").fetchone()
    return fila[0] if fila else None


def completar_cuentas(con):
    """Deja una cuenta para cada empleado y cada usuario que todavía no la tenga."""
    admin = con.execute("SELECT id_cuenta, id_empleado FROM cuenta WHERE usuario = 'admin'").fetchone()
    if not admin:
        _nueva_cuenta(con, "admin", CLAVE_ADMIN, "Administrador",
                      id_empleado=_empleado_para_admin(con))
    elif admin["id_empleado"] is None:
        # la cuenta se creó cuando todavía no había empleados: se enlaza ahora
        empleado = _empleado_para_admin(con)
        if empleado:
            con.execute("UPDATE cuenta SET id_empleado = ? WHERE id_cuenta = ?",
                        (empleado, admin["id_cuenta"]))
    for e in con.execute("SELECT * FROM empleado WHERE estado = 'Activo'").fetchall():
        if not con.execute("SELECT 1 FROM cuenta WHERE id_empleado = ? AND rol = 'Empleado'",
                           (e["id_empleado"],)).fetchone() \
                and not con.execute("SELECT 1 FROM cuenta WHERE usuario = ?",
                                    (e["usuario_sistema"],)).fetchone():
            _nueva_cuenta(con, e["usuario_sistema"], CLAVE_EMPLEADO, "Empleado",
                          id_empleado=e["id_empleado"])
    for u in con.execute("SELECT * FROM usuario").fetchall():
        if not con.execute("SELECT 1 FROM cuenta WHERE id_usuario = ?",
                           (u["id_usuario"],)).fetchone():
            usuario = nombre_de_cuenta_para(con, u["nombre"], u["apellido"], u["correo"])
            _nueva_cuenta(con, usuario, CLAVE_LECTOR, "Lector", id_usuario=u["id_usuario"])
    con.commit()


def preparar(con):
    crear_tablas(con)
    completar_cuentas(con)


# ----------------------------------------------------------------------
# Bitácora
# ----------------------------------------------------------------------
def _ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def registrar(con, sesion, accion, detalle="", usuario=None):
    """Guarda una línea en la bitácora. Nunca debe romper el programa."""
    try:
        equipo = f"{socket.gethostname()} ({getpass.getuser()})"
    except Exception:
        equipo = "desconocido"
    try:
        con.execute(
            "INSERT INTO bitacora (fecha_hora, usuario, rol, accion, detalle, equipo) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (_ahora(), usuario or (sesion.usuario if sesion else None),
             sesion.rol if sesion else None, accion, detalle, equipo))
        con.commit()
    except Exception:
        pass


def listar_bitacora(con, texto="", limite=500):
    t = f"%{texto.strip()}%"
    return con.execute(
        "SELECT * FROM bitacora WHERE usuario LIKE ? OR accion LIKE ? OR detalle LIKE ? "
        "OR rol LIKE ? ORDER BY id_bitacora DESC LIMIT ?", (t, t, t, t, limite)).fetchall()


def ultimo_acceso(con, usuario):
    """Fecha del inicio de sesión anterior al actual (None si es la primera vez)."""
    fila = con.execute(
        "SELECT fecha_hora FROM bitacora WHERE usuario = ? AND accion = 'Inicio de sesión' "
        "ORDER BY id_bitacora DESC LIMIT 1 OFFSET 1", (usuario,)).fetchone()
    return fila[0] if fila else None


# ----------------------------------------------------------------------
# Entrar, salir y cambiar la clave
# ----------------------------------------------------------------------
def _intentos_recientes(con, usuario):
    desde = (datetime.now() - timedelta(minutes=MINUTOS_BLOQUEO)).strftime("%Y-%m-%d %H:%M:%S")
    ultimo_ok = con.execute(
        "SELECT MAX(fecha_hora) FROM bitacora WHERE lower(usuario) = lower(?) "
        "AND accion = 'Inicio de sesión'",
        (usuario,)).fetchone()[0]
    if ultimo_ok and ultimo_ok > desde:
        desde = ultimo_ok
    return con.execute(
        "SELECT COUNT(*) FROM bitacora WHERE lower(usuario) = lower(?) "
        "AND accion = 'Intento fallido' AND fecha_hora >= ?", (usuario, desde)).fetchone()[0]


def _nombre_real(con, fila):
    if fila["id_usuario"]:
        u = con.execute("SELECT nombre, apellido FROM usuario WHERE id_usuario = ?",
                        (fila["id_usuario"],)).fetchone()
    else:
        u = con.execute("SELECT nombre, apellido FROM empleado WHERE id_empleado = ?",
                        (fila["id_empleado"],)).fetchone()
    return f"{u['nombre']} {u['apellido']}" if u else fila["usuario"]


def autenticar(con, usuario, clave):
    """Devuelve la Sesion si los datos son correctos; si no, lanza ErrorSeguridad."""
    usuario = (usuario or "").strip()
    if not usuario or not clave:
        raise ErrorSeguridad("Escribe tu usuario y tu contraseña.")
    if _intentos_recientes(con, usuario) >= MAX_INTENTOS:
        registrar(con, None, "Acceso bloqueado", "Demasiados intentos fallidos", usuario)
        raise ErrorSeguridad(f"Demasiados intentos. Espera {MINUTOS_BLOQUEO} minutos.")
    fila = con.execute("SELECT * FROM cuenta WHERE lower(usuario) = lower(?) AND activa = 1",
                       (usuario,)).fetchone()
    if not fila or not hmac.compare_digest(fila["clave_hash"], _hash(clave, fila["sal"])):
        registrar(con, None, "Intento fallido", "Usuario o contraseña incorrectos", usuario)
        raise ErrorSeguridad("Usuario o contraseña incorrectos.")
    sesion = Sesion(fila["id_cuenta"], fila["usuario"], fila["rol"], _nombre_real(con, fila),
                    fila["id_empleado"], fila["id_usuario"])
    registrar(con, sesion, "Inicio de sesión", f"Entró como {sesion.rol}")
    return sesion


def cambiar_clave(con, sesion, actual, nueva, repetida):
    fila = con.execute("SELECT * FROM cuenta WHERE id_cuenta = ?", (sesion.id_cuenta,)).fetchone()
    if not hmac.compare_digest(fila["clave_hash"], _hash(actual, fila["sal"])):
        registrar(con, sesion, "Cambio de contraseña rechazado", "La contraseña actual no coincide")
        raise ErrorSeguridad("La contraseña actual no es correcta.")
    if len(nueva) < 6:
        raise ErrorSeguridad("La contraseña nueva debe tener al menos 6 caracteres.")
    if nueva != repetida:
        raise ErrorSeguridad("Las contraseñas nuevas no coinciden.")
    sal = secrets.token_hex(16)
    con.execute("UPDATE cuenta SET clave_hash = ?, sal = ? WHERE id_cuenta = ?",
                (_hash(nueva, sal), sal, sesion.id_cuenta))
    con.commit()
    registrar(con, sesion, "Cambio de contraseña", "Contraseña actualizada")
