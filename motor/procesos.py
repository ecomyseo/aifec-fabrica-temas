"""AIFEC — motor de fábrica: lanzar procesos con límite de tiempo y pararlos enteros.

Un proceso se para por su PID con la API de cada plataforma: en Windows, con `ctypes`
(instantánea Toolhelp32 y `TerminateProcess`, de las hojas a la raíz); en los demás, con el
grupo de procesos. Ningún programa externo hace de intermediario.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path

TIEMPO_AGOTADO = "tiempo agotado"

_WINDOWS = os.name == "nt"

if _WINDOWS:  # pragma: no cover - según la plataforma
    import ctypes
    from ctypes import wintypes

    _k32 = ctypes.WinDLL("kernel32", use_last_error=True)

    class _Entrada(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", ctypes.c_wchar * 260),
        ]

    _k32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    _k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    _k32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(_Entrada)]
    _k32.Process32FirstW.restype = wintypes.BOOL
    _k32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(_Entrada)]
    _k32.Process32NextW.restype = wintypes.BOOL
    _k32.CloseHandle.argtypes = [wintypes.HANDLE]
    _k32.CloseHandle.restype = wintypes.BOOL
    _k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    _k32.OpenProcess.restype = wintypes.HANDLE
    _k32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    _k32.TerminateProcess.restype = wintypes.BOOL
    _k32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    _k32.GetExitCodeProcess.restype = wintypes.BOOL
    _k32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    _k32.QueryFullProcessImageNameW.restype = wintypes.BOOL

    _SNAPSHOT_PROCESOS = 0x00000002
    _PROCESS_TERMINATE = 0x0001
    _PROCESS_QUERY_LIMITED = 0x1000
    _STILL_ACTIVE = 259
    _INVALIDO = ctypes.c_void_p(-1).value


def _tabla_windows() -> dict:
    """pid -> (pid del padre, nombre del ejecutable) con una instantánea Toolhelp32."""
    tabla = {}
    instantanea = _k32.CreateToolhelp32Snapshot(_SNAPSHOT_PROCESOS, 0)
    if instantanea in (None, 0, _INVALIDO):
        return tabla
    try:
        entrada = _Entrada()
        entrada.dwSize = ctypes.sizeof(_Entrada)
        hay = _k32.Process32FirstW(instantanea, ctypes.byref(entrada))
        while hay:
            tabla[int(entrada.th32ProcessID)] = (int(entrada.th32ParentProcessID), entrada.szExeFile)
            hay = _k32.Process32NextW(instantanea, ctypes.byref(entrada))
    finally:
        _k32.CloseHandle(instantanea)
    return tabla


def _padres_posix() -> dict:
    """pid -> pid del padre, leyendo /proc (si no existe, vacío: se confía en el grupo)."""
    padres = {}
    proc = Path("/proc")
    if not proc.is_dir():
        return padres
    for carpeta in proc.iterdir():
        if not carpeta.name.isdigit():
            continue
        try:
            texto = (carpeta / "stat").read_text(errors="replace")
            resto = texto.rsplit(")", 1)[1].split()
            padres[int(carpeta.name)] = int(resto[1])
        except (OSError, IndexError, ValueError):
            continue
    return padres


def descendientes(pid: int) -> list:
    """Todos los procesos que cuelgan de `pid`, de los más cercanos a los más lejanos."""
    if _WINDOWS:
        padres = {p: datos[0] for p, datos in _tabla_windows().items()}
    else:
        padres = _padres_posix()
    por_padre = {}
    for hijo, padre in padres.items():
        por_padre.setdefault(padre, []).append(hijo)
    visto = {pid}
    resultado = []
    cola = [pid]
    while cola:
        actual = cola.pop(0)
        for hijo in por_padre.get(actual, []):
            if hijo not in visto:
                visto.add(hijo)
                resultado.append(hijo)
                cola.append(hijo)
    return resultado


def _nombre_windows(manejador) -> str:
    tam = wintypes.DWORD(1024)
    buffer = ctypes.create_unicode_buffer(1024)
    if _k32.QueryFullProcessImageNameW(manejador, 0, buffer, ctypes.byref(tam)):
        return os.path.basename(buffer.value).lower()
    return ""


def vivo(pid: int, nombre: str = None) -> bool:
    """¿Sigue vivo el proceso `pid`? Con `nombre`, además, su ejecutable tiene que contenerlo
    (así un PID que ya ha reutilizado otro programa no cuenta como el nuestro)."""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    if _WINDOWS:
        manejador = _k32.OpenProcess(_PROCESS_QUERY_LIMITED, False, pid)
        if not manejador:
            # Sin permiso para mirarlo: existe, pero no se puede comprobar de quién es.
            return ctypes.get_last_error() == 5 and nombre is None
        try:
            codigo = wintypes.DWORD(0)
            if not _k32.GetExitCodeProcess(manejador, ctypes.byref(codigo)):
                return False
            if codigo.value != _STILL_ACTIVE:
                return False
            if nombre is None:
                return True
            return nombre.lower() in _nombre_windows(manejador)
        finally:
            _k32.CloseHandle(manejador)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        pass
    except OSError:
        return False
    try:
        texto = Path("/proc/%d/stat" % pid).read_text(errors="replace")
        if texto.rsplit(")", 1)[1].split()[0] == "Z":
            return False
    except (OSError, IndexError):
        pass
    if nombre is None:
        return True
    candidatos = []
    for fichero in ("comm",):
        try:
            candidatos.append(Path("/proc/%d/%s" % (pid, fichero)).read_text(errors="replace").strip())
        except OSError:
            pass
    try:
        candidatos.append(os.path.basename(os.readlink("/proc/%d/exe" % pid)))
    except OSError:
        pass
    if not candidatos:
        return True  # no hay /proc: no se puede comprobar el nombre, se da por bueno
    return any(nombre.lower() in c.lower() for c in candidatos)


def _matar_uno(pid: int) -> None:
    if pid <= 4 or pid == os.getpid():
        return
    if _WINDOWS:
        manejador = _k32.OpenProcess(_PROCESS_TERMINATE, False, pid)
        if manejador:
            try:
                _k32.TerminateProcess(manejador, 1)
            finally:
                _k32.CloseHandle(manejador)
        return
    try:
        if os.getpgid(pid) == pid and pid != os.getpgrp():
            os.killpg(pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        pass
    try:
        os.kill(pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        pass


def matar_arbol(pid: int) -> None:
    """Mata `pid` y todo lo que cuelga de él, de las hojas a la raíz, hasta que no quede nada."""
    for _ in range(5):
        desc = descendientes(pid)
        for hijo in reversed(desc):
            _matar_uno(hijo)
        _matar_uno(pid)
        if not desc:
            break
        time.sleep(0.05)
    for hijo in descendientes(pid):
        _matar_uno(hijo)


def lanzar(orden: list, cwd, salida, minutos, entorno: dict = None):
    """Lanza `orden` (programa y argumentos) en `cwd`, con la salida a un fichero.

    Devuelve el código de salida, o `TIEMPO_AGOTADO` si se pasó de `minutos` (y entonces mata el
    árbol entero). Sin ventana en Windows y con la entrada vacía. Si el programa no existe,
    devuelve 127 y lo apunta en el fichero de salida.
    """
    salida = Path(salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    opciones = {"cwd": str(cwd), "stdin": subprocess.DEVNULL, "stderr": subprocess.STDOUT}
    if _WINDOWS:
        opciones["creationflags"] = (getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
                                     | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200))
    else:
        opciones["start_new_session"] = True
    if entorno is not None:
        entorno_completo = dict(os.environ)
        entorno_completo.update(entorno)
        opciones["env"] = entorno_completo
    with open(salida, "ab") as fichero:
        opciones["stdout"] = fichero
        try:
            proceso = subprocess.Popen([str(a) for a in orden], **opciones)
        except OSError as error:
            fichero.write(("No se pudo lanzar %r: %s\n" % (orden[0] if orden else "", error)).encode("utf-8"))
            return 127
        limite = None if minutos is None else float(minutos) * 60.0
        try:
            return proceso.wait(timeout=limite)
        except subprocess.TimeoutExpired:
            matar_arbol(proceso.pid)
            try:
                proceso.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pass
            return TIEMPO_AGOTADO
