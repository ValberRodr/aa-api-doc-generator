"""Gera o trecho de código Python (didático, usando `requests`) mostrado no
relatório para cada endpoint. Assume que a autenticação (seção inicial do
relatório) já foi feita e que existe uma `session` com o header
`X-Authorization` configurado."""
from __future__ import annotations

from .catalog import Endpoint

AUTH_SNIPPET = '''\
import requests

base_url = "https://sua-control-room.exemplo.com"  # SEM barra no final
proxies = None
verify_tls = True

# Se sua rede exige saída via proxy HTTP corporativo para alcançar a
# Control Room, descomente as linhas abaixo. Alguns proxies corporativos
# fazem inspeção de TLS (reemitem um certificado próprio no meio do túnel);
# se esse certificado tiver algum defeito que o OpenSSL rejeite mesmo sendo
# aceito pelo seu sistema operacional, pode ser necessário desligar a
# verificação SÓ nesta chamada via proxy — nunca em conexão direta.
#
# proxies = {"http": "http://proxy.empresa.com:80", "https": "http://proxy.empresa.com:80"}
# verify_tls = False

session = requests.Session()
if proxies:
    session.proxies = proxies
session.verify = verify_tls

resp = session.post(
    f"{base_url}/v2/authentication",
    json={"username": "SEU_USUARIO", "apiKey": "SUA_API_KEY"},
    timeout=20,
)
resp.raise_for_status()
token = resp.json()["token"]

# Toda chamada seguinte usa este header — NUNCA "Authorization: Bearer ...".
session.headers.update({"X-Authorization": token})
'''


def render_snippet(ep: Endpoint, resolved_path: str) -> str:
    lines = [f'# {ep.summary}']
    if ep.method == "GET":
        lines.append(f'resp = session.get(f"{{base_url}}{resolved_path}", timeout=20)')
    else:
        body_repr = "{\n    ...\n}" if ep.is_action or ep.body_builder else "None"
        if ep.body_builder:
            sample_body = ep.body_builder({})
            body_repr = repr(sample_body)
        lines.append(f'body = {body_repr}')
        method_call = {"POST": "post", "PUT": "put", "PATCH": "patch", "DELETE": "delete"}[ep.method]
        lines.append(f'resp = session.{method_call}(f"{{base_url}}{resolved_path}", json=body, timeout=20)')
    lines.append("resp.raise_for_status()")
    lines.append("data = resp.json()")
    return "\n".join(lines)
