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
