"""Gera exemplos de gráfico a partir de dados agregados — nunca a partir de
registros individuais. Cada função aqui recebe uma LISTA DE ITENS já
coletada (ver `report.py::_collect_chart_items`, que busca uma amostra maior
só para contar, sem guardar os registros crus) e devolve só contagens —
muito mais seguro de embutir no relatório do que uma amostra de JSON real, e
é o nível de informação que de fato importa para monitoramento.

Os gráficos de distribuição usam Mermaid `pie` (suportado nativamente em
GitHub, VS Code e no visualizador de artifacts). As séries no tempo usam uma
barra de texto simples (funciona em qualquer lugar que mostre texto
monoespaçado, sem depender de uma versão específica do Mermaid)."""
from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

BAR_CHAR = "█"
MAX_BAR_WIDTH = 40


def _mermaid_pie(title: str, counts: Counter) -> str:
    lines = ["```mermaid", "pie showData", f"    title {title}"]
    for label, value in counts.most_common():
        safe_label = (label or "(vazio)").replace('"', "'")
        lines.append(f'    "{safe_label}" : {value}')
    lines.append("```")
    return "\n".join(lines)


def _text_bars(title: str, counts: dict[str, int]) -> str:
    if not counts:
        return ""
    max_value = max(counts.values()) or 1
    lines = [f"{title}", ""]
    width = max((len(k) for k in counts), default=0)
    for label in sorted(counts):
        value = counts[label]
        bar_len = max(1, round(value / max_value * MAX_BAR_WIDTH)) if value else 0
        bar = BAR_CHAR * bar_len
        lines.append(f"{label.ljust(width)}  {bar} {value}")
    return "```\n" + "\n".join(lines) + "\n```"


def activity_status_chart(items: list[dict[str, Any]]) -> tuple[str, str] | None:
    """(gráfico de pizza por status, barra de execuções/dia)."""
    if not items:
        return None
    status_counts = Counter((it.get("status") or "DESCONHECIDO") for it in items)
    pie = _mermaid_pie(f"Execuções por status (amostra de {len(items)})", status_counts)

    per_day: Counter = Counter()
    for it in items:
        raw = it.get("startDateTime") or it.get("created") or ""
        day = raw[:10] if isinstance(raw, str) and len(raw) >= 10 else None
        if day:
            per_day[day] += 1
    bars = _text_bars("Execuções por dia (amostra)", dict(per_day)) if per_day else ""
    return pie, bars


def devices_status_chart(items: list[dict[str, Any]]) -> tuple[str, str] | None:
    if not items:
        return None
    counts = Counter((it.get("status") or "DESCONHECIDO") for it in items)
    pie = _mermaid_pie(f"Dispositivos por status (amostra de {len(items)})", counts)
    return pie, ""


def scheduler_status_chart(items: list[dict[str, Any]]) -> tuple[str, str] | None:
    if not items:
        return None
    counts = Counter((it.get("status") or "DESCONHECIDO") for it in items)
    pie = _mermaid_pie(f"Agendamentos por status (amostra de {len(items)})", counts)
    return pie, ""


def audit_actions_chart(items: list[dict[str, Any]]) -> tuple[str, str] | None:
    if not items:
        return None
    counts = Counter((it.get("action") or it.get("auditType") or "DESCONHECIDO") for it in items)
    pie = _mermaid_pie(f"Eventos de auditoria por ação (amostra de {len(items)})", counts)
    return pie, ""


def users_roles_chart(items: list[dict[str, Any]]) -> tuple[str, str] | None:
    if not items:
        return None
    counts: Counter = Counter()
    for it in items:
        name = it.get("name") or it.get("roleName") or "DESCONHECIDO"
        counts[name] += 1
    pie = _mermaid_pie(f"Papéis cadastrados (amostra de {len(items)})", counts)
    return pie, ""


CHART_BUILDERS = {
    "activity_status": activity_status_chart,
    "devices_status": devices_status_chart,
    "scheduler_status": scheduler_status_chart,
    "audit_actions": audit_actions_chart,
    "users_roles": users_roles_chart,
}


PYTHON_CHART_SNIPPETS = {
    "activity_status": '''\
import matplotlib.pyplot as plt
from collections import Counter

# `items` = lista completa de activity.list (pagine até ter o período que
# quiser — veja a paginação em "Como chamar em Python" acima).
status_counts = Counter(item["status"] for item in items)

fig, ax = plt.subplots()
ax.pie(status_counts.values(), labels=status_counts.keys(), autopct="%1.0f%%")
ax.set_title("Execuções por status")
plt.savefig("execucoes_por_status.png")
''',
    "devices_status": '''\
import matplotlib.pyplot as plt
from collections import Counter

status_counts = Counter(item["status"] for item in items)
fig, ax = plt.subplots()
ax.bar(status_counts.keys(), status_counts.values())
ax.set_ylabel("Dispositivos")
plt.savefig("dispositivos_por_status.png")
''',
}
