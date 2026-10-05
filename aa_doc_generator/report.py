from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .catalog import ENDPOINTS, Endpoint
from .charts import CHART_BUILDERS, PYTHON_CHART_SNIPPETS
from .client import AAClient
from .introspect import SENSITIVE_KEY_HINTS, extract_schema
from .mock import MOCK_CHART_ITEMS, MOCK_RESPONSES
from .snippets import AUTH_SNIPPET, render_snippet

STATUS_LABEL = {
    "OK": "✅ OK",
    "FORBIDDEN": "🔒 Não licenciado/permitido (403)",
    "UNAVAILABLE": "⬜ Não disponível nesta Control Room (404)",
    "ERROR": "❌ Erro",
    "SKIPPED": "⏭️ Pulado",
    "NOT_ATTEMPTED": "🚫 Não chamado automaticamente",
    "ACTION_DOCUMENTED": "⚠️ Ação (documentada, não executada)",
}


@dataclass
class EndpointResult:
    endpoint: Endpoint
    status: str
    http_status: int | None = None
    sample: Any = None
    schema: list = field(default_factory=list)
    error: str = ""
    resolved_path: str = ""
    chart_md: str = ""  # gráfico(s) já renderizados (agregados, sem registro crú)


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            k_norm = k.lower().replace("-", "").replace("_", "")
            if any(h.replace("_", "") in k_norm for h in SENSITIVE_KEY_HINTS):
                out[k] = "***REDACTED***"
            else:
                out[k] = _redact(v)
        return out
    if isinstance(value, list):
        return [_redact(v) for v in value]
    return value


def _truncate_lists(value: Any, limit: int, depth: int = 0) -> Any:
    if depth > 8:
        return value
    if isinstance(value, dict):
        return {k: _truncate_lists(v, limit, depth + 1) for k, v in value.items()}
    if isinstance(value, list):
        return [_truncate_lists(v, limit, depth + 1) for v in value[:limit]]
    return value


def _resolve_path(ep: Endpoint, context: dict[str, Any], size: int) -> str | None:
    path = ep.path
    for p in ep.path_params:
        if p not in context:
            return None
        path = path.replace("{" + p + "}", str(context[p]))
    return path.replace("{size}", str(size))


def _fetch_chart_items(client: AAClient, ep: Endpoint, context: dict[str, Any], chart_sample_size: int) -> list[dict[str, Any]]:
    """Busca uma amostra maior SÓ para agregar em gráfico — os itens somem do
    escopo assim que `charts.py` termina de contá-los; nunca entram no
    relatório como registro individual (ver `EndpointResult.chart_md`, que
    carrega só o gráfico já renderizado)."""
    chart_ctx = dict(context, page_size=chart_sample_size)
    resolved_path = _resolve_path(ep, context, chart_sample_size)
    if resolved_path is None:
        return []
    body = ep.body_builder(chart_ctx) if ep.body_builder else None
    try:
        resp = client.call(ep.method, resolved_path, body=body)
    except Exception:
        return []
    if resp.status_code < 200 or resp.status_code >= 300:
        return []
    try:
        data = resp.json()
    except ValueError:
        return []
    items = data.get("list") if isinstance(data, dict) else None
    return items if isinstance(items, list) else []


def run_catalog(
    client: AAClient | None,
    max_list_items: int = 5,
    categories: set[str] | None = None,
    mock: bool = False,
    chart_sample_size: int = 100,
) -> list[EndpointResult]:
    results: list[EndpointResult] = []
    context: dict[str, Any] = {}

    for ep in ENDPOINTS:
        if categories and ep.category not in categories:
            continue
        if ep.key == "auth.login":
            continue
        if ep.is_action:
            results.append(EndpointResult(ep, "ACTION_DOCUMENTED", resolved_path=ep.path))
            continue
        if not ep.probe_safe:
            results.append(EndpointResult(
                ep, "NOT_ATTEMPTED", error="Marcado no catálogo como não seguro para chamada automática.",
                resolved_path=ep.path,
            ))
            continue

        resolved_path = _resolve_path(ep, context, max_list_items)
        if resolved_path is None:
            results.append(EndpointResult(
                ep, "SKIPPED", error="Dependia de um ID obtido em outra chamada que não retornou itens.",
                resolved_path=ep.path,
            ))
            continue

        body = ep.body_builder(dict(context, page_size=max_list_items)) if ep.body_builder else None

        if mock:
            data = MOCK_RESPONSES.get(ep.key, {})
            http_status = 200
        else:
            assert client is not None
            try:
                resp = client.call(ep.method, resolved_path, body=body)
            except Exception as exc:
                results.append(EndpointResult(ep, "ERROR", error=str(exc), resolved_path=resolved_path))
                continue
            http_status = resp.status_code
            if http_status == 403:
                results.append(EndpointResult(ep, "FORBIDDEN", http_status=403, resolved_path=resolved_path))
                continue
            if http_status in (404, 501):
                results.append(EndpointResult(ep, "UNAVAILABLE", http_status=http_status, resolved_path=resolved_path))
                continue
            if http_status < 200 or http_status >= 300:
                results.append(EndpointResult(
                    ep, "ERROR", http_status=http_status, error=resp.text[:300], resolved_path=resolved_path,
                ))
                continue
            try:
                data = resp.json()
            except ValueError:
                results.append(EndpointResult(
                    ep, "ERROR", http_status=http_status, error="Resposta não é JSON.", resolved_path=resolved_path,
                ))
                continue

        sample = _redact(_truncate_lists(data, max_list_items))
        schema = extract_schema(sample)

        chart_md = ""
        if ep.chart:
            builder = CHART_BUILDERS.get(ep.chart)
            if builder:
                if mock:
                    chart_items = MOCK_CHART_ITEMS.get(ep.key, [])
                else:
                    chart_items = _fetch_chart_items(client, ep, context, chart_sample_size)
                chart_result = builder(chart_items)
                if chart_result:
                    pie, bars = chart_result
                    chart_md = "\n\n".join(part for part in (pie, bars) if part)

        results.append(EndpointResult(
            ep, "OK", http_status=http_status, sample=sample, schema=schema,
            resolved_path=resolved_path, chart_md=chart_md,
        ))

        if ep.key == "activity.list":
            items = (data.get("list") or []) if isinstance(data, dict) else []
            if items and isinstance(items[0], dict):
                first_id = items[0].get("id") or items[0].get("activityId")
                if first_id:
                    context["activityId"] = first_id

    return results


def render_report(
    base_url: str,
    username: str,
    generated_at: str,
    results: list[EndpointResult],
    max_list_items: int,
    mock: bool,
) -> str:
    lines: list[str] = []
    w = lines.append

    w("# Documentação da API — Automation Anywhere Control Room")
    w("")
    w(f"- **Gerado em:** {generated_at}")
    w(f"- **Control Room:** `{base_url}`")
    w(f"- **Usuário usado na coleta:** `{username}`")
    w(f"- **Itens de lista por chamada:** {max_list_items} (truncado de propósito)")
    if mock:
        w("")
        w("> ⚠️ **RELATÓRIO DE EXEMPLO (`--mock`)** — todos os dados abaixo são fictícios, "
          "gerados sem conexão com nenhuma Control Room real. Serve só para mostrar o "
          "formato do relatório.")
    else:
        w("")
        w("> ⚠️ **Este relatório contém dados reais de produção** (truncados e com campos "
          "sensíveis redigidos). **Não** faça commit deste arquivo nem o envie para "
          "repositórios compartilhados — mantenha-o só localmente (`output/` já está no "
          "`.gitignore` deste projeto).")
    w("")

    w("## Como ler este relatório")
    w("")
    w("Para cada chamada da API você encontra, nesta ordem:")
    w("")
    w("1. **O que é** — descrição em linguagem simples.")
    w("2. **📊 O que monitorar** — perguntas de negócio/operação que esse retorno ajuda a responder.")
    w("3. **Gráfico de exemplo**, quando aplicável — agregado a partir de uma amostra maior (nunca um "
      "registro individual real).")
    w("4. **Como chamar em Python** — trecho pronto para copiar.")
    w("5. **Campos observados** e uma **amostra da resposta** (pequena, redigida).")
    w("")

    w("## Sumário")
    w("")
    w("| Categoria | Endpoint | Método | Caminho | Status |")
    w("|---|---|---|---|---|")
    for r in results:
        display_path = (r.resolved_path or r.endpoint.path).replace("{size}", str(max_list_items))
        w(f"| {r.endpoint.category} | {r.endpoint.summary} | `{r.endpoint.method}` | `{display_path}` | {STATUS_LABEL[r.status]} |")
    w("")

    w("## Como autenticar")
    w("")
    w("Toda chamada documentada abaixo assume que você já executou isto uma vez:")
    w("")
    w("```python")
    w(AUTH_SNIPPET.rstrip())
    w("```")
    w("")

    categories_seen: list[str] = []
    for r in results:
        if r.endpoint.category not in categories_seen:
            categories_seen.append(r.endpoint.category)

    for category in categories_seen:
        w(f"## {category}")
        w("")
        for r in results:
            if r.endpoint.category != category:
                continue
            ep = r.endpoint
            w(f"### {ep.summary}")
            w("")
            heading_path = (r.resolved_path or ep.path).replace("{size}", str(max_list_items))
            w(f"`{ep.method} {heading_path}`" + ("  —  **[AÇÃO — modifica estado, nunca executada automaticamente]**" if ep.is_action else ""))
            w("")
            w(ep.description)
            if ep.notes:
                w("")
                w(f"**Notas:** {ep.notes}")
            w("")

            if ep.monitoring:
                w("**📊 O que monitorar com este retorno:**")
                w("")
                for idea in ep.monitoring:
                    w(f"- {idea}")
                w("")

            w(f"**Status nesta coleta:** {STATUS_LABEL[r.status]}" + (f" (HTTP {r.http_status})" if r.http_status else ""))
            if r.error:
                w("")
                w(f"> {r.error}")
            w("")

            if ep.is_action:
                if ep.expected_request_fields:
                    w("**Corpo esperado da requisição (documentado — confira contra a versão da sua Control Room antes de usar):**")
                    w("")
                    w("| Campo | Tipo | Descrição |")
                    w("|---|---|---|")
                    for fname, ftype, fdesc in ep.expected_request_fields:
                        w(f"| `{fname}` | {ftype} | {fdesc} |")
                    w("")
            elif ep.expected_request_fields:
                w("**Campos do corpo da requisição:**")
                w("")
                w("| Campo | Tipo | Descrição |")
                w("|---|---|---|")
                for fname, ftype, fdesc in ep.expected_request_fields:
                    w(f"| `{fname}` | {ftype} | {fdesc} |")
                w("")

            if r.status == "OK":
                if r.chart_md:
                    w("**📈 Gráfico de exemplo** (agregado a partir de uma amostra maior, sem expor registro individual):")
                    w("")
                    w(r.chart_md)
                    w("")
                    py_chart = PYTHON_CHART_SNIPPETS.get(ep.chart or "")
                    if py_chart:
                        w("Para reproduzir com o histórico completo (não só a amostra):")
                        w("")
                        w("```python")
                        w(py_chart.rstrip())
                        w("```")
                        w("")

                w("**Como chamar em Python:**")
                w("")
                w("```python")
                w(render_snippet(ep, r.resolved_path))
                w("```")
                w("")
                if r.schema:
                    w("**Campos observados na resposta real:**")
                    w("")
                    w("| Campo | Tipo | Exemplo |")
                    w("|---|---|---|")
                    for f in r.schema:
                        example = f.example.replace("|", "\\|").replace("\n", " ")
                        w(f"| `{f.path}` | {f.type_name} | {example} |")
                    w("")
                w("**Amostra da resposta (truncada, campos sensíveis redigidos):**")
                w("")
                w("```json")
                w(json.dumps(r.sample, indent=2, ensure_ascii=False))
                w("```")
            elif not ep.is_action:
                w("**Como chamar em Python (formato esperado — não foi possível validar contra uma resposta real nesta coleta):**")
                w("")
                w("```python")
                w(render_snippet(ep, r.resolved_path or ep.path))
                w("```")
            w("")

    return "\n".join(lines)
