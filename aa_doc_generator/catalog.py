"""Catálogo de chamadas da API do Automation Anywhere Control Room.

Cada `Endpoint` descreve UMA chamada: método, caminho, se é segura para
chamar automaticamente durante a geração do relatório (`probe_safe`) ou se é
uma ação que MODIFICA estado na Control Room (`is_action` — deploy, pausar,
excluir, criar, etc.), que o gerador nunca executa sozinho, só documenta.

Os caminhos marcados com `confirmed=True` foram validados em produção pelo
projeto RPA Observability Package (ver server.py, classe
AutomationAnywhereGateway). Os demais são o desenho conhecido/publicado da
API do Control Room, mas podem variar por versão — o relatório gerado por
esta ferramenta sempre mostra o que a SUA Control Room respondeu de verdade;
trate as descrições aqui como ponto de partida, não como garantia.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Endpoint:
    key: str
    category: str
    method: str
    path: str
    summary: str
    description: str
    confirmed: bool = False
    is_action: bool = False
    probe_safe: bool = False
    path_params: tuple[str, ...] = ()
    body_builder: Callable[[dict[str, Any]], dict[str, Any] | None] | None = None
    expected_request_fields: tuple[tuple[str, str, str], ...] = ()  # (campo, tipo, descrição)
    notes: str = ""


def _list_body(page_size: int = 5) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def _build(_ctx: dict[str, Any]) -> dict[str, Any]:
        return {"sort": [], "page": {"offset": 0, "length": page_size}}

    return _build


ENDPOINTS: list[Endpoint] = [
    # ---------------------------------------------------------------- Auth
    Endpoint(
        key="auth.login",
        category="Autenticação",
        method="POST",
        path="/v2/authentication",
        summary="Autentica usuário + API Key e devolve o token de sessão.",
        description=(
            "Primeira chamada de qualquer integração. O token devolvido vai "
            "no header `X-Authorization` de toda chamada seguinte. Não tem "
            "prefixo `Bearer` — é só o valor do token."
        ),
        confirmed=True,
        probe_safe=False,  # já é chamada explicitamente pelo AAClient.authenticate()
        expected_request_fields=(
            ("username", "string", "Usuário da Control Room (ou conta de serviço)."),
            ("apiKey", "string", "API Key gerada em Minha Conta > API Key."),
        ),
        notes="Resposta inclui `token` e, em algumas versões, `devicePoolIds` e informações de licença.",
    ),
    # ------------------------------------------------------------ Activity
    Endpoint(
        key="activity.list",
        category="Activity",
        method="POST",
        path="/v3/activity/list",
        summary="Lista execuções (deployments) de bots, com paginação.",
        description=(
            "Equivalente à aba 'Activity' da Control Room. `page` é um "
            "OBJETO `{offset, length}` — mandar um número solto devolve "
            "HTTP 400 (json.deserialization.exception), erro já visto em "
            "produção."
        ),
        confirmed=True,
        probe_safe=True,
        body_builder=_list_body(),
        notes=(
            "Campos de data vêm como `startDateTime`/`endDateTime` (ISO 8601), "
            "não `started`/`ended`. Não existe campo de duração pronto — "
            "calcule a diferença entre os dois timestamps."
        ),
    ),
    Endpoint(
        key="activity.detail",
        category="Activity",
        method="GET",
        path="/v3/activity/execution/{activityId}",
        summary="Detalhe de uma execução específica.",
        description="Mesmo formato de item da Activity List, para um `activityId` específico.",
        confirmed=True,
        probe_safe=True,
        path_params=("activityId",),
        notes="O gerador usa automaticamente o primeiro ID retornado por activity.list, se houver.",
    ),
    Endpoint(
        key="activity.deploy",
        category="Activity",
        method="POST",
        path="/v3/automations/deploy",
        summary="[AÇÃO] Dispara a execução (deploy) de uma automação em um ou mais dispositivos.",
        description=(
            "Inicia um bot de verdade em produção. Esta ferramenta NUNCA "
            "chama este endpoint automaticamente — só documenta o formato "
            "esperado do corpo da requisição."
        ),
        is_action=True,
        expected_request_fields=(
            ("fileId", "number", "ID do arquivo/automação no Repositório a ser executado."),
            ("runAsUserIds", "array<number>", "IDs dos usuários cujas credenciais de Device rodam o bot."),
            ("poolIds", "array<number>", "IDs de Device Pools onde distribuir a execução (alternativa a deviceIds)."),
            ("deviceIds", "array<number>", "IDs de devices específicos (alternativa a poolIds)."),
            ("botInput", "object", "Parâmetros de entrada do bot, como um dicionário de variáveis tipadas."),
        ),
    ),
    Endpoint(
        key="activity.stop",
        category="Activity",
        method="PUT",
        path="/v2/activity/stop/{activityId}",
        summary="[AÇÃO] Interrompe (stop) uma execução em andamento.",
        description="Encerra à força uma automação rodando. Nunca executado automaticamente por esta ferramenta.",
        is_action=True,
        path_params=("activityId",),
    ),
    Endpoint(
        key="activity.pause_resume",
        category="Activity",
        method="PUT",
        path="/v2/activity/{action}/{activityId}",
        summary="[AÇÃO] Pausa ou retoma uma execução em andamento (action = pause|resume).",
        description="Nunca executado automaticamente por esta ferramenta.",
        is_action=True,
        path_params=("action", "activityId"),
    ),
    # ------------------------------------------------------------- Devices
    Endpoint(
        key="devices.list",
        category="Dispositivos (Devices)",
        method="GET",
        path="/v2/devices/list?page=0&size=5",
        summary="Lista os dispositivos (Bot Runners / máquinas) registrados.",
        description="Equivalente à aba 'Devices'. Traz status de conexão, pool, tipo e versão do agente.",
        confirmed=True,
        probe_safe=True,
    ),
    Endpoint(
        key="devices.pools",
        category="Dispositivos (Devices)",
        method="GET",
        path="/v1/devices/pools/list?page=0&size=5",
        summary="Lista os Device Pools (grupos de dispositivos).",
        description="Pools são usados para distribuir execuções entre várias máquinas.",
        probe_safe=True,
    ),
    # ----------------------------------------------------------- Scheduler
    Endpoint(
        key="scheduler.list",
        category="Agendamentos (Scheduler)",
        method="GET",
        path="/v2/schedule/rules/list?page=0&size=5",
        summary="Lista as regras de agendamento configuradas.",
        description="Cada regra liga uma automação a um calendário (cron/recorrência) e a dispositivos/pools de destino.",
        confirmed=True,
        probe_safe=True,
    ),
    Endpoint(
        key="scheduler.toggle",
        category="Agendamentos (Scheduler)",
        method="PATCH",
        path="/v2/schedule/rules/{scheduleId}",
        summary="[AÇÃO] Habilita/desabilita uma regra de agendamento.",
        description="Nunca executado automaticamente por esta ferramenta.",
        is_action=True,
        path_params=("scheduleId",),
        expected_request_fields=(("enabled", "boolean", "true para habilitar, false para desabilitar."),),
    ),
    # ---------------------------------------------------------- Repositório
    Endpoint(
        key="repository.workspaces",
        category="Repositório",
        method="GET",
        path="/v2/repository/workspaces",
        summary="Lista os workspaces (Public/Private) do Repositório.",
        description="Workspace é o nível mais alto de organização de pastas/arquivos de automação.",
        confirmed=True,
        probe_safe=True,
    ),
    Endpoint(
        key="repository.folders",
        category="Repositório",
        method="POST",
        path="/v2/repository/folders/list",
        summary="Lista pastas do Repositório.",
        description="Estrutura de pastas dentro de um workspace.",
        probe_safe=True,
        body_builder=_list_body(),
    ),
    Endpoint(
        key="repository.files",
        category="Repositório",
        method="POST",
        path="/v2/repository/files/list",
        summary="Lista arquivos (bots/tasks) do Repositório.",
        description="Cada item representa uma automação armazenada — nome, tipo, pasta, última modificação.",
        probe_safe=True,
        body_builder=_list_body(),
    ),
    Endpoint(
        key="packages.list",
        category="Pacotes (Packages)",
        method="GET",
        path="/v2/packages/list?page=0&size=5",
        summary="Lista os pacotes (comandos/plugins) instalados na Control Room.",
        description="Inclui nome, versão e se o pacote está habilitado.",
        confirmed=True,
        probe_safe=True,
    ),
    # -------------------------------------------------------------- Audit
    Endpoint(
        key="audit.logs",
        category="Auditoria",
        method="GET",
        path="/v2/audit/logs?page=0&size=5",
        summary="Lista eventos de auditoria (quem fez o quê, quando).",
        description="Cobre login, deploy, alterações de usuário/papel, mudanças de pacote, etc., conforme a versão.",
        confirmed=True,
        probe_safe=True,
    ),
    # ------------------------------------------------------------- Policy
    Endpoint(
        key="policy.list",
        category="Políticas (Policy)",
        method="GET",
        path="/v3/policies?page=0&size=5",
        summary="Lista políticas de controle (ex.: restrições de execução).",
        description="Recurso licenciado separadamente — normal responder 403 (FORBIDDEN) se não estiver habilitado.",
        confirmed=True,
        probe_safe=True,
    ),
    # ----------------------------------------------------------------- WLM
    Endpoint(
        key="wlm.queues",
        category="Workload Management (WLM)",
        method="GET",
        path="/v2/wlm/queues?page=0&size=5",
        summary="Lista filas de trabalho do Workload Management.",
        description="Recurso licenciado separadamente — normal responder UNAVAILABLE se o módulo não existir.",
        confirmed=True,
        probe_safe=True,
    ),
    # ------------------------------------------------------------------ ACC
    Endpoint(
        key="acc.summary",
        category="AARI / ACC",
        method="GET",
        path="/v2/acc/summary",
        summary="Resumo do módulo AARI/ACC (interação humano-bot), se licenciado.",
        description="Recurso licenciado separadamente.",
        confirmed=True,
        probe_safe=True,
    ),
    # ------------------------------------------------------------- Insight
    Endpoint(
        key="insight.summary",
        category="Bot Insight",
        method="GET",
        path="/v2/insight/summary",
        summary="Resumo de métricas do Bot Insight, se licenciado.",
        description="Recurso licenciado separadamente.",
        confirmed=True,
        probe_safe=True,
    ),
    # ------------------------------------------------------- User Mgmt
    Endpoint(
        key="users.search",
        category="Usuários",
        method="POST",
        path="/v1/usermanagement/users/list",
        summary="Busca/lista usuários da Control Room.",
        description=(
            "Diferente das demais 'List API' (que aceitam GET), a busca de "
            "usuários é POST — confirmado em produção."
        ),
        confirmed=True,
        probe_safe=True,
        body_builder=_list_body(),
    ),
    Endpoint(
        key="roles.list",
        category="Usuários",
        method="GET",
        path="/v1/usermanagement/roles/list?page=0&size=5",
        summary="Lista papéis (roles) configurados.",
        description="Cada papel agrega um conjunto de licenças/permissões atribuível a usuários.",
        probe_safe=True,
    ),
    # --------------------------------------------------------- Credential
    Endpoint(
        key="credentials.list",
        category="Cofre de Credenciais",
        method="GET",
        path="/v2/credentialvault/credentials?page=0&size=5",
        summary="Lista credenciais cadastradas no Cofre (metadados — nunca o valor secreto).",
        description="A API nunca devolve o valor da credencial em texto puro, só metadados (nome, dono, atributos).",
        probe_safe=True,
    ),
    Endpoint(
        key="credentials.create",
        category="Cofre de Credenciais",
        method="POST",
        path="/v2/credentialvault/credentials",
        summary="[AÇÃO] Cria uma nova credencial no Cofre.",
        description="Nunca executado automaticamente por esta ferramenta.",
        is_action=True,
        expected_request_fields=(
            ("name", "string", "Nome da credencial."),
            ("description", "string", "Descrição opcional."),
            ("attributes", "array<object>", "Lista de atributos {name, type, value/masked}."),
        ),
    ),
]


def by_category() -> dict[str, list[Endpoint]]:
    grouped: dict[str, list[Endpoint]] = {}
    for ep in ENDPOINTS:
        grouped.setdefault(ep.category, []).append(ep)
    return grouped
