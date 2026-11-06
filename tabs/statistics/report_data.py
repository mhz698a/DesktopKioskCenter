"""Agregaciones de dominio para las gráficas de procedencia y accesos."""
from __future__ import annotations

from collections import defaultdict


UAQ_FULL_NAME = "Universidad Autónoma de Querétaro"
PUBLIC_GENERAL_LABEL = "Público en general"


def build_chart_data(rows, grouping):
    """Devuelve datos ordenados para las tres gráficas de estadísticas.

    La procedencia general consolida todas las facultades y los trabajadores UAQ
    en una única categoría. La gráfica de facultades conserva cada facultad
    como una categoría independiente.
    """
    period_totals = defaultdict(int)
    general_origins = defaultdict(int)
    faculties = defaultdict(int)

    for row in rows:
        period = str(row.get("period") or "")
        origin = str(row.get("origin") or "Sin clasificar")
        source = str(row.get("source") or "Sin especificar")
        total = max(0, int(row.get("total") or 0))

        period_totals[period] += total

        if origin == "UAQ":
            general_origins[UAQ_FULL_NAME] += total
            if source != "Trabajador interno":
                faculties[source] += total
        elif origin == "Universidad":
            general_origins[source] += total
        elif origin == PUBLIC_GENERAL_LABEL:
            general_origins[PUBLIC_GENERAL_LABEL] += total
        else:
            general_origins[origin] += total

    period_data = []
    for period, total in sorted(period_totals.items()):
        if grouping == "day":
            label = f"{period[8:10]}/{period[5:7]}"
        elif grouping == "week":
            label = f"Sem {period[8:10]}/{period[5:7]}"
        elif grouping == "month":
            label = f"{period[5:7]}/{period[:4]}"
        else:
            raise ValueError("La agrupación debe ser day, week o month.")
        period_data.append((label, total))

    general_data = sorted(
        general_origins.items(), key=lambda item: (-item[1], item[0].casefold())
    )
    faculty_data = sorted(
        faculties.items(), key=lambda item: (-item[1], item[0].casefold())
    )
    return period_data, general_data, faculty_data
