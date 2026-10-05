# Política de segurança

Esta ferramenta se conecta a um Automation Anywhere Control Room de
produção usando credenciais reais. Resumo das decisões de segurança — ver
também a seção "Segurança" do [README](README.md).

## Manuseio de credenciais

- A API Key só é aceita via variável de ambiente (`AA_API_KEY`) ou prompt
  interativo (`getpass`) — nunca via argumento de linha de comando.
- O token de sessão retornado pela Control Room vive só em memória
  (`AAClient.session`, header `X-Authorization`) e nunca é escrito em disco,
  log ou mensagem de erro.
- Nenhuma exceção interna inclui o corpo da requisição ou headers — só
  código de status HTTP e, no máximo, um trecho curto do corpo da
  *resposta* de erro (nunca da requisição, que é onde a credencial viajaria).

## Redação de dados sensíveis

Qualquer campo de uma resposta real cujo nome contenha um dos padrões em
`aa_doc_generator/introspect.py::SENSITIVE_KEY_HINTS` (senha, token, api
key, secret, credential, cpf, cnpj, etc.) tem o **valor** substituído por
`***REDACTED***` antes de entrar no schema extraído ou na amostra JSON
embutida no relatório. O nome do campo continua visível — é estrutura da
API, não segredo.

## Ações nunca executadas automaticamente

Endpoints marcados como `is_action=True` no catálogo (deploy de bot, parar/
pausar execução, criar credencial, alternar agendamento, ...) são **só
documentados** — a ferramenta nunca os chama por conta própria, mesmo em
modo não-interativo. Se você quiser testar um desses endpoints, copie o
trecho Python gerado e execute manualmente, com atenção.

## Dados de produção nunca versionados

`output/` está no `.gitignore`. Relatórios gerados contra uma Control Room
real contêm dados reais (mesmo truncados e parcialmente redigidos) e nunca
devem ser commitados neste repositório público. O único relatório versionado
é `examples/sample_report.md`, gerado com `--mock` — inteiramente fictício.

## Proxy corporativo e TLS

Por padrão, a verificação do certificado TLS está sempre ativa. A flag
`--insecure-proxy-tls` só desliga essa verificação quando `--proxy` também
está configurado — nunca em conexão direta — e existe para contornar
proxies corporativos que fazem inspeção de TLS com um certificado
reemitido defeituoso (falta de extensão X.509 esperada, por exemplo), que o
validador do OpenSSL rejeita mesmo quando o sistema operacional aceita.
Trate essa flag como um contorno temporário, não uma configuração
permanente — o ideal é corrigir o certificado do proxy.

## Reportando um problema

Se você encontrar uma vulnerabilidade real nesta ferramenta (não no
Automation Anywhere em si), abra uma issue no repositório descrevendo o
cenário, sem incluir nenhuma credencial ou dado real de nenhuma Control
Room.
