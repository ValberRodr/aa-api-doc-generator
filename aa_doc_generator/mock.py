"""Dados fictícios usados só pelo modo `--mock` da CLI — serve para gerar um
relatório de EXEMPLO (committed no repositório, em examples/sample_report.md)
sem nunca precisar de uma Control Room real nem de dados de produção. Nenhum
valor aqui tem qualquer relação com um ambiente real."""
from __future__ import annotations

from typing import Any

MOCK_RESPONSES: dict[str, Any] = {
    "activity.list": {
        "page": {"offset": 0, "total": 2, "totalElements": 2},
        "list": [
            {
                "id": "123456789012345",
                "automationName": "Exemplo_ProcessarFaturas",
                "status": "COMPLETED",
                "startDateTime": "2026-01-10T08:00:00Z",
                "endDateTime": "2026-01-10T08:04:12Z",
                "deviceName": "BOTRUNNER-EXEMPLO-01",
                "botRunnerUserId": 42,
                "workDeviceId": 7,
            }
        ],
    },
    "activity.detail": {
        "id": "123456789012345",
        "automationName": "Exemplo_ProcessarFaturas",
        "status": "COMPLETED",
        "startDateTime": "2026-01-10T08:00:00Z",
        "endDateTime": "2026-01-10T08:04:12Z",
        "deviceName": "BOTRUNNER-EXEMPLO-01",
    },
    "devices.list": {
        "page": {"totalElements": 1},
        "list": [
            {
                "id": 7,
                "hostName": "BOTRUNNER-EXEMPLO-01",
                "status": "CONNECTED",
                "type": "BOT_RUNNER",
                "poolName": "Pool Exemplo",
                "osVersion": "Windows Server 2019",
            }
        ],
    },
    "devices.pools": {"list": [{"id": 1, "name": "Pool Exemplo", "deviceCount": 1}]},
    "scheduler.list": {
        "list": [
            {
                "id": 55,
                "name": "Exemplo_Agendamento_Diario",
                "fileId": 901,
                "status": "ENABLED",
                "cronString": "0 6 * * *",
            }
        ]
    },
    "repository.workspaces": {"list": [{"id": 1, "name": "Public", "type": "PUBLIC"}]},
    "repository.folders": {"list": [{"id": 10, "name": "Processos Financeiro", "parentId": 1}]},
    "repository.files": {
        "list": [{"id": 901, "name": "Exemplo_ProcessarFaturas", "type": "TASK_BOT", "folderId": 10}]
    },
    "packages.list": {"list": [{"name": "Excel Advanced Package", "version": "25.1.0", "enabled": True}]},
    "audit.logs": {
        "list": [
            {
                "timestamp": "2026-01-10T08:00:00Z",
                "userName": "svc_exemplo",
                "action": "DEPLOY",
                "targetName": "Exemplo_ProcessarFaturas",
            }
        ]
    },
    "policy.list": {"list": []},
    "wlm.queues": {"list": []},
    "acc.summary": {},
    "insight.summary": {},
    "users.search": {
        "list": [{"id": 1, "username": "exemplo.usuario", "email": "exemplo@empresa.local", "disabled": False}]
    },
    "roles.list": {"list": [{"id": 2, "name": "AAE_Basic"}]},
    "credentials.list": {"list": [{"id": 3, "name": "Credencial Exemplo", "owner": "exemplo.usuario"}]},
}

# Amostra maior e mais variada, usada só para desenhar o GRÁFICO de exemplo
# do modo `--mock` (nunca aparece como registro individual no relatório —
# ver `charts.py`, que só devolve contagens agregadas).
MOCK_CHART_ITEMS: dict[str, list[dict[str, Any]]] = {
    "activity.list": (
        [{"status": "COMPLETED", "startDateTime": f"2026-01-{d:02d}T08:00:00Z"} for d in range(1, 11) for _ in range(3)]
        + [{"status": "RUN_FAILED", "startDateTime": f"2026-01-{d:02d}T09:00:00Z"} for d in range(1, 11) for _ in range(1)]
        + [{"status": "RUNNING", "startDateTime": "2026-01-10T10:00:00Z"}]
    ),
    "devices.list": (
        [{"status": "CONNECTED"} for _ in range(8)] + [{"status": "DISCONNECTED"} for _ in range(2)]
    ),
    "scheduler.list": (
        [{"status": "ENABLED"} for _ in range(12)] + [{"status": "DISABLED"} for _ in range(3)]
    ),
    "audit.logs": (
        [{"action": "DEPLOY"} for _ in range(9)]
        + [{"action": "LOGIN"} for _ in range(15)]
        + [{"action": "PACKAGE_UPDATED"} for _ in range(4)]
        + [{"action": "USER_ROLE_CHANGED"} for _ in range(2)]
    ),
    "roles.list": (
        [{"name": "AAE_Basic"} for _ in range(18)]
        + [{"name": "AAE_Bot Runner"} for _ in range(6)]
        + [{"name": "AAE_Admin"} for _ in range(2)]
    ),
}
