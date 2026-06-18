"""Aplana estructuras anidadas a notación de punto (p. ej. attributes.http.method).

Permite exponer cualquier campo anidado de una signal/log como columna seleccionable,
sin tener que listarlo a mano. Cada hoja del objeto se convierte en una clave plana.
"""
from typing import Any, Dict


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
