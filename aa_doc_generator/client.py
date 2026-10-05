"""Cliente HTTP para o Automation Anywhere Control Room.

Reproduz, de forma genérica e sem depender de nenhuma infraestrutura
específica de uma empresa, a lógica de conexão validada em produção pelo
projeto RPA Observability Package:

1. Autenticação via POST /v2/authentication (body {username, apiKey}),
   devolvendo um token que vai no header `X-Authorization` em toda chamada
   seguinte (NUNCA em `Authorization`/Bearer — a API da Automation Anywhere
   usa um header próprio).
2. Suporte a proxy HTTP corporativo (host:port), usado em redes que exigem
   saída via proxy para alcançar a Control Room.
3. Quando um proxy está configurado, a verificação do certificado TLS é
   desligada SÓ para essa chamada via proxy — nunca no modo direto. Isso
   existe porque alguns proxies corporativos fazem inspeção de TLS
   reemitindo um certificado próprio no meio do túnel, e esse certificado
   pode ter defeitos que o validador do OpenSSL (usado pelo Python) rejeita
   mesmo sendo aceito pelo sistema operacional. Se a sua rede não tem esse
   problema, prefira não desligar a verificação (ver README, seção
   "Conexão via proxy corporativo").

Nunca grava API Key nem token em disco, log ou exceção — eles só existem em
memória, dentro da sessão HTTP.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Any

import requests


class AAAuthError(Exception):
    """Credenciais rejeitadas pela Control Room."""


class AAConnectionError(Exception):
    """Falha de rede/transporte ao tentar alcançar a Control Room."""


@dataclass
class AAConnectionConfig:
    base_url: str
    username: str
    api_key: str
    proxy: str | None = None  # "host:port"
    verify_tls: bool | None = None  # None = decide automaticamente (ver _configure_transport)
    timeout: int = 20


class AAClient:
    """Sessão autenticada contra uma Control Room real. Não tem modo mock —
    quem precisar de dados simulados para testes deve usar
    `aa_doc_generator.catalog` com `--mock` na CLI, que não usa esta classe."""

    def __init__(self, config: AAConnectionConfig):
        self.config = config
        self.token: str | None = None
        self.session = requests.Session()
        self._configure_transport()

    def _configure_transport(self) -> None:
        cfg = self.config
        if cfg.proxy:
            proxy_url = f"http://{cfg.proxy}"
            self.session.proxies = {"http": proxy_url, "https": proxy_url}
            verify = cfg.verify_tls if cfg.verify_tls is not None else False
            self.session.verify = verify
            if not verify:
                warnings.filterwarnings(
                    "ignore", message="Unverified HTTPS request"
                )
        else:
            self.session.verify = cfg.verify_tls if cfg.verify_tls is not None else True

    @property
    def base_url(self) -> str:
        return self.config.base_url.rstrip("/")

    def authenticate(self) -> str:
        url = f"{self.base_url}/v2/authentication"
        try:
            resp = self.session.post(
                url,
                json={"username": self.config.username, "apiKey": self.config.api_key},
                timeout=self.config.timeout,
            )
        except requests.exceptions.RequestException as exc:
            raise AAConnectionError(str(exc)) from exc
        if resp.status_code in (401, 403):
            raise AAAuthError("Usuário ou API Key inválidos (HTTP %d)." % resp.status_code)
        if resp.status_code < 200 or resp.status_code >= 300:
            raise AAConnectionError(f"Control Room retornou HTTP {resp.status_code}.")
        try:
            data = resp.json()
        except ValueError as exc:
            raise AAAuthError("Resposta inesperada da Control Room (não é JSON).") from exc
        token = data.get("token")
        if not token:
            raise AAAuthError("Control Room não retornou token de autenticação.")
        self.token = token
        self.session.headers.update({"X-Authorization": token})
        return token

    def call(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> requests.Response:
        """Uma chamada autenticada. `path` deve começar com /v1, /v2, /v3 ou
        /v4 — já formatado (parâmetros de rota como {activityId} resolvidos
        pelo chamador antes de vir aqui)."""
        if self.token is None:
            raise AAAuthError("Chame authenticate() antes de call().")
        url = f"{self.base_url}{path}"
        try:
            return self.session.request(
                method, url, json=body, params=params, timeout=self.config.timeout
            )
        except requests.exceptions.RequestException as exc:
            raise AAConnectionError(str(exc)) from exc
