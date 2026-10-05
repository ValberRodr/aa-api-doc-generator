"""CLI: `python -m aa_doc_generator --base-url ... --username ...`

Nunca aceita a API Key como argumento de linha de comando (ficaria no
histórico do shell e em `ps`) — ela vem de variável de ambiente
(`AA_API_KEY`) ou de um prompt interativo (`getpass`, não aparece na tela).
"""
from __future__ import annotations

import argparse
import getpass
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from .client import AAAuthError, AAClient, AAConnectionConfig, AAConnectionError
from .report import render_report, run_catalog

STATUS_ORDER = ["OK", "FORBIDDEN", "UNAVAILABLE", "ERROR", "SKIPPED", "NOT_ATTEMPTED", "ACTION_DOCUMENTED"]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="aa-doc-generator",
        description="Gera documentação da API do Automation Anywhere Control Room a partir de chamadas reais.",
    )
    p.add_argument("--base-url", default=os.environ.get("AA_BASE_URL", ""), help="URL da Control Room, ex.: https://cr.empresa.com")
    p.add_argument("--username", default=os.environ.get("AA_USERNAME", ""), help="Usuário (ou conta de serviço).")
    p.add_argument("--proxy", default=os.environ.get("AA_PROXY", ""), help="Proxy HTTP corporativo host:port, se a rede exigir.")
    p.add_argument("--insecure-proxy-tls", action="store_true",
                    default=os.environ.get("AA_PROXY_INSECURE_TLS", "") == "1",
                    help="Desliga a verificação de certificado TLS ao usar --proxy (só se o proxy fizer inspeção TLS com certificado defeituoso).")
    p.add_argument("--output-dir", default="output", help="Pasta onde salvar o relatório (default: ./output).")
    p.add_argument("--max-list-items", type=int, default=5, help="Itens por lista incluídos no relatório (default: 5).")
    p.add_argument("--categories", default="", help="Filtra por categorias, separadas por vírgula (default: todas).")
    p.add_argument("--mock", action="store_true", help="Gera um relatório de EXEMPLO com dados fictícios, sem conectar a nenhuma Control Room.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    categories = {c.strip() for c in args.categories.split(",") if c.strip()} or None

    if args.mock:
        base_url_label = "mock://exemplo"
        username_label = "usuario.exemplo"
        results = run_catalog(client=None, max_list_items=args.max_list_items, categories=categories, mock=True)
    else:
        if not args.base_url:
            print("Erro: informe --base-url (ou AA_BASE_URL).", file=sys.stderr)
            return 2
        if not args.username:
            print("Erro: informe --username (ou AA_USERNAME).", file=sys.stderr)
            return 2
        api_key = os.environ.get("AA_API_KEY") or getpass.getpass("API Key da Control Room: ")
        if not api_key:
            print("Erro: API Key vazia.", file=sys.stderr)
            return 2

        config = AAConnectionConfig(
            base_url=args.base_url,
            username=args.username,
            api_key=api_key,
            proxy=args.proxy or None,
            verify_tls=(False if (args.proxy and args.insecure_proxy_tls) else None),
        )
        client = AAClient(config)
        try:
            client.authenticate()
        except AAAuthError as exc:
            print(f"Falha de autenticação: {exc}", file=sys.stderr)
            return 1
        except AAConnectionError as exc:
            print(f"Falha de conexão: {exc}", file=sys.stderr)
            print("Se sua rede exige proxy corporativo, use --proxy host:port.", file=sys.stderr)
            return 1

        print(f"Autenticado em {config.base_url} como {config.username}.")
        base_url_label = config.base_url
        username_label = config.username
        results = run_catalog(client=client, max_list_items=args.max_list_items, categories=categories, mock=False)

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    report_md = render_report(
        base_url=base_url_label,
        username=username_label,
        generated_at=generated_at,
        results=results,
        max_list_items=args.max_list_items,
        mock=args.mock,
    )

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    suffix = "mock" if args.mock else "producao"
    out_path = out_dir / f"aa_api_doc_{suffix}_{timestamp}.md"
    out_path.write_text(report_md, encoding="utf-8")

    counts: dict[str, int] = {}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1
    summary = ", ".join(f"{s}={counts[s]}" for s in STATUS_ORDER if s in counts)
    print(f"Relatório salvo em: {out_path}")
    print(f"Resumo: {summary}")
    if not args.mock:
        print("Lembrete: este arquivo tem dados reais truncados — não faça commit dele.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
