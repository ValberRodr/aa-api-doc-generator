"""Varre uma resposta JSON real da Control Room e extrai um schema de campos
(nome do caminho, tipo, exemplo) — é isso que vira a tabela "Campos
observados" de cada endpoint no relatório. Nomes de campo sensíveis têm o
VALOR redigido antes de qualquer coisa ser guardada ou impressa; o nome do
campo continua aparecendo (é estrutura da API, não segredo)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SENSITIVE_KEY_HINTS = (
    "password", "senha", "secret", "apikey", "api_key", "token",
    "authorization", "credential", "cred_", "ssn", "cpf", "cnpj",
    "clientsecret", "privatekey", "accesskey",
)

MAX_DEPTH = 6
MAX_FIELDS = 300
MAX_STRING_LEN = 120


@dataclass
class FieldInfo:
    path: str
    type_name: str
    example: str


def _is_sensitive(key: str) -> bool:
    k = key.lower().replace("-", "").replace("_", "")
    return any(hint.replace("_", "") in k for hint in SENSITIVE_KEY_HINTS)


def _type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _example(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return ""
    text = "null" if value is None else str(value)
    if len(text) > MAX_STRING_LEN:
        text = text[:MAX_STRING_LEN] + "…"
    return text


def extract_schema(payload: Any, prefix: str = "") -> list[FieldInfo]:
    """Caminha recursivamente por `payload`. Para arrays, examina só o
    primeiro item (representativo) — evita duplicar o mesmo schema N vezes
    quando a resposta é uma lista de 50 objetos iguais em formato."""
    fields: list[FieldInfo] = []
    _walk(payload, prefix, fields, depth=0)
    # dedup preservando ordem — list_builder pode repetir caminhos quando a
    # lista tem itens com formato ligeiramente diferente entre si.
    seen: set[str] = set()
    deduped: list[FieldInfo] = []
    for f in fields:
        if f.path in seen:
            continue
        seen.add(f.path)
        deduped.append(f)
        if len(deduped) >= MAX_FIELDS:
            break
    return deduped


def _walk(value: Any, path: str, out: list[FieldInfo], depth: int) -> None:
    if depth > MAX_DEPTH or len(out) >= MAX_FIELDS:
        return
    if isinstance(value, dict):
        for key, sub in value.items():
            sub_path = f"{path}.{key}" if path else key
            if _is_sensitive(key):
                out.append(FieldInfo(sub_path, _type_name(sub), "***REDACTED***"))
                continue
            out.append(FieldInfo(sub_path, _type_name(sub), _example(sub)))
            _walk(sub, sub_path, out, depth + 1)
    elif isinstance(value, list):
        if value:
            _walk(value[0], f"{path}[]", out, depth + 1)
