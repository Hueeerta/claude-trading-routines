"""Overlay: lectura no vinculante de Claude (sentimiento/fundamental) registrada
junto al trade. NO afecta la ejecución; sirve para medir, a lo largo de N trades,
si el criterio de Claude agrega valor sobre la regla determinista. Si lo demuestra,
se codifica en reglas (no antes).
"""
from __future__ import annotations

from . import ledger


def registrar(texto: str, position_id: str | None = None) -> None:
    """Guarda la lectura paralela en el journal del ledger."""
    ledger.record_journal(texto, kind="overlay", position_id=position_id)
