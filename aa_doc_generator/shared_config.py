"""Reaproveita, de propósito, a MESMA lógica de rede/config já corrigida em
produção pelo projeto irmão (RPA Ops Monitor — pasta `RPA_Observability_Package_v3`,
classe `AutomationAnywhereGateway` em `server.py`): esta ferramenta deve
funcionar na mesma rede corporativa sem precisar redescobrir nada que já foi
resolvido lá.

Duas particularidades herdadas de lá (confirmado explicitamente pelo
responsável do projeto que replicar esses valores aqui é intencional — eles
já são públicos no repositório irmão `RPA_LOG_Dashboard`, não é informação
nova sendo exposta):

1. **Proxy HTTP corporativo por padrão no Windows.** O firewall de perímetro
   dessa rede só libera saída para a internet através de um proxy — conectar
   direto na Control Room trava em timeout. `RPA_MONITOR_AA_PROXY`/`AA_PROXY`
   sempre vencem quando definidos; sem eles, no Windows, cai no mesmo proxy
   padrão já usado pelo painel principal. Fora do Windows, não há proxy
   nenhum por padrão.
2. **Config não-sensível compartilhada.** Se o painel principal já está
   configurado nesta máquina/rede, `aa_config.json` (`CONFIG_ROOT/aa_config.json`,
   mesmo `CONFIG_ROOT` dele) já tem `aaBaseUrl`/`aaUsername` — esta ferramenta
   lê o mesmo arquivo para não pedir de novo o que você já digitou uma vez.
   Nunca lê nem escreve nenhum segredo ali (a API Key nunca é persistida,
   nem aqui nem no painel principal).

Tudo isso continua 100% sobrescrevível por variável de ambiente/flag de CLI
— ver README, seção "Conexão"."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Mesmos literais usados pelo RPA Ops Monitor nesta rede corporativa — já
# públicos no repositório irmão (ver server.py, DEFAULT_DATA_ROOT /
# DEFAULT_AA_PROXY). Servem só de valor-padrão quando nada é configurado
# explicitamente; nunca são segredo.
_DEFAULT_DATA_ROOT_WIN = (
    r"\\d7156ws1011\DirGeralAdmFin\Organizaçao&Processos\Melhoria_Continua\Monitoramento"
)
_DEFAULT_AA_PROXY_WIN = "proxy.bradseg.com.br:80"


def resolve_proxy() -> str | None:
    """Precedência: --proxy (tratado no cli.py) > AA_PROXY > RPA_MONITOR_AA_PROXY
    (reaproveita o mesmo env var do painel principal, se já estiver setado
    nesta máquina) > padrão do Windows > nenhum proxy."""
    explicit = os.environ.get("AA_PROXY")
    if explicit:
        return explicit
    shared = os.environ.get("RPA_MONITOR_AA_PROXY")
    if shared:
        return shared
    if sys.platform.startswith("win"):
        return _DEFAULT_AA_PROXY_WIN
    return None


def _config_root() -> Path:
    override = os.environ.get("RPA_MONITOR_CONFIG_ROOT")
    if override:
        return Path(override)
    data_root = os.environ.get("RPA_MONITOR_DATA_ROOT")
    if not data_root and sys.platform.startswith("win"):
        data_root = _DEFAULT_DATA_ROOT_WIN
    if data_root:
        return Path(data_root) / "Cadastro_RPA"
    return Path.home() / ".aa_doc_generator"


def load_shared_config() -> dict[str, str]:
    """Lê `aa_config.json` do MESMO local usado pelo painel principal — só
    `baseUrl`/`username`, nunca segredo. Arquivo ausente/corrompido não é
    erro: devolve dict vazio, quem chamar decide o que fazer."""
    path = _config_root() / "aa_config.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {
        "baseUrl": (raw.get("aaBaseUrl") or "").rstrip("/"),
        "username": raw.get("aaUsername") or "",
    }
