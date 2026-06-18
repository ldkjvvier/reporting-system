"""Aplana estructuras anidadas a notación de punto (p. ej. attributes.http.method).

Permite exponer cualquier campo anidado de una signal/log como columna seleccionable,
sin tener que listarlo a mano. Cada hoja del objeto se convierte en una clave plana.
"""
from typing import Any, Dict, List


def parse_scope(scope: str) -> Dict[str, str]:
    """Desglosa el 'scope' de una serie de métrica ('k1:v1,k2:v2,...') en columnas.

    Datadog devuelve, por cada serie agrupada con 'by {tagA,tagB}', un scope con los
    pares tag:valor de esa serie. Separarlos permite ofrecer cada tag como columna
    seleccionable del reporte, en vez de una sola celda 'scope' con todo apelmazado.

    - scope '*' o vacío        -> {} (sin tags)
    - 'action:block,app:web'   -> {'action': 'block', 'app': 'web'}
    - claves con punto (usr.id) se respetan tal cual.
    """
    out: Dict[str, str] = {}
    s = (scope or "").strip()
    if not s or s == "*":
        return out
    for pair in s.split(","):
        pair = pair.strip()
        if not pair:
            continue
        key, sep, value = pair.partition(":")
        key = key.strip()
        if key:
            out[key] = value.strip() if sep else ""
    return out


def parse_group_by(query: str) -> List[str]:
    """Extrae las claves de agrupación de 'by {tagA,tagB,...}' en una query de métrica."""
    import re

    m = re.search(r"by\s*\{([^}]*)\}", query or "")
    if not m:
        return []
    return [t.strip() for t in m.group(1).split(",") if t.strip()]


def flatten_record(record: Any, prefix: str = "") -> Dict[str, Any]:
    """Convierte un dict/lista anidado en un dict plano con claves en notación de punto.

    - dict            -> recurre como 'clave.subclave'
    - lista de escalares -> se une con ', ' (una sola celda)
    - lista con objetos  -> se indexa: 'clave.0.subclave'
    - escalares       -> se dejan tal cual
    """
    out: Dict[str, Any] = {}
    if isinstance(record, dict):
        for k, v in record.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            out.update(flatten_record(v, key))
    elif isinstance(record, (list, tuple)):
        if record and all(not isinstance(x, (dict, list, tuple)) for x in record):
            out[prefix] = ", ".join("" if x is None else str(x) for x in record)
        else:
            for i, x in enumerate(record):
                out.update(flatten_record(x, f"{prefix}.{i}"))
    elif prefix:
        out[prefix] = record
    return out
