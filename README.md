# AA API Doc Generator

Gera documentação completa da API REST do **Automation Anywhere Control Room**
a partir de chamadas reais contra o seu ambiente — autenticação, campos
observados em cada resposta, exemplos de dados reais (truncados e com campos
sensíveis redigidos) e trechos de código Python prontos para reutilizar.

Não é um app do Automation Anywhere nem substitui a documentação oficial —
é uma ferramenta de introspecção: ela chama os endpoints de leitura da sua
própria Control Room e documenta **o que ela respondeu de verdade**, em vez
de depender de descrições genéricas que variam entre versões.

## O que ele faz

1. Autentica em `POST /v2/authentication` com usuário + API Key.
2. Para cada endpoint de **leitura** do catálogo (`aa_doc_generator/catalog.py`),
   faz a chamada real (lista truncada a poucos itens) e:
   - extrai o schema de campos observados (nome, tipo, exemplo);
   - redige automaticamente qualquer campo com nome sensível (senha, token,
     API key, credencial, etc.) antes de guardar ou imprimir qualquer coisa;
   - gera o trecho de Python equivalente à chamada;
   - explica, em linguagem simples, **o que monitorar** com aquele retorno
     (taxa de erro, SLA, dispositivos desconectados, etc.);
   - para os endpoints mais usados em dashboards (Activity, Devices,
     Scheduler, Audit, Roles), busca uma amostra **maior** só para gerar um
     **gráfico de exemplo** (pizza de status, barra de volume por dia) —
     esses itens extra nunca entram no relatório como registro individual,
     só como contagem agregada.
3. Para endpoints de **ação** (deploy de bot, parar execução, criar
   credencial, habilitar/desabilitar agendamento, ...), **nunca chama
   automaticamente** — só documenta o formato esperado da requisição, com um
   aviso claro de que é preciso confirmar contra a versão da sua Control Room
   antes de usar.
4. Salva tudo em um único relatório Markdown em `output/` (pasta no
   `.gitignore` — ver "Segurança" abaixo).

## Uso

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Veja o formato do relatório sem conectar a nada (dados 100% fictícios):
python -m aa_doc_generator --mock

# Contra a sua Control Room real:
python -m aa_doc_generator --base-url https://sua-control-room.exemplo.com --username seu.usuario
# -> pede a API Key via prompt (não aparece na tela, não fica no histórico do shell)
```

Variáveis de ambiente equivalentes (úteis em CI ou para não digitar toda
vez): `AA_BASE_URL`, `AA_USERNAME`, `AA_API_KEY`.

### Conexão — particularidades do ambiente de produção

Esta ferramenta reaproveita de propósito a mesma lógica de rede/config já
corrigida em produção pelo projeto irmão (o painel **RPA Ops Monitor**,
`aa_doc_generator/shared_config.py`), para funcionar "de fábrica" na mesma
rede sem precisar reconfigurar nada:

1. **Proxy HTTP corporativo por padrão no Windows.** O firewall de perímetro
   dessa rede só libera saída para a internet através de um proxy — conectar
   direto na Control Room trava em timeout. No Windows, sem nada configurado,
   a ferramenta já usa o mesmo proxy padrão do painel principal. Fora do
   Windows (mac/Linux/CI), não há proxy por padrão. Precedência completa:
   `--proxy` explícito > `AA_PROXY` > `RPA_MONITOR_AA_PROXY` (reaproveita o
   mesmo env var do painel principal, se já estiver setado nesta máquina) >
   padrão do Windows > nenhum proxy. Use `--proxy none` para forçar conexão
   direta mesmo no Windows.
2. **Config não-sensível compartilhada.** Se o painel principal (`RPA Ops
   Monitor`) já está configurado nesta máquina, `--base-url`/`--username`
   nem precisam ser digitados de novo — a ferramenta lê o mesmo
   `aa_config.json` (mesmo `CONFIG_ROOT`) que ele usa. Nunca lê nem grava
   nenhum segredo ali — a API Key continua só por env var/prompt.

Alguns proxies corporativos fazem **inspeção de TLS**: eles reemitem um
certificado próprio no meio da conexão HTTPS. Se esse certificado tiver um
defeito que o validador do OpenSSL (usado pelo Python) rejeite — mesmo sendo
aceito pelo seu sistema operacional —, a chamada falha com
`CERTIFICATE_VERIFY_FAILED`. Nesse caso específico, e só nesse caso, use:

```bash
python -m aa_doc_generator --insecure-proxy-tls
```

Isso desliga a verificação do certificado **só na chamada feita através do
proxy** — nunca na conexão direta. Prefira sempre corrigir o certificado do
proxy junto do time de TI em vez de usar esta flag indefinidamente; ela
existe para destravar o uso imediato quando isso não está ao seu alcance.

Para conectar numa Control Room fora dessa rede (outro cliente/ambiente),
basta sobrescrever tudo explicitamente:

```bash
python -m aa_doc_generator --base-url https://outra-control-room.exemplo.com --username outro.usuario --proxy none
```

### Outras opções

| Flag | Efeito |
|---|---|
| `--categories "Activity,Dispositivos (Devices)"` | Só gera as categorias listadas. |
| `--max-list-items 10` | Quantos itens de cada lista entram no relatório como amostra (default: 5). |
| `--chart-sample-size 200` | Quantos itens buscar só para alimentar os gráficos agregados (default: 100) — nunca aparecem como registro crú no relatório. |
| `--output-dir ./meus-relatorios` | Onde salvar (default: `./output`). |

## Segurança

- **A API Key nunca é aceita como argumento de linha de comando** — só por
  variável de ambiente ou prompt interativo (`getpass`), para não ficar no
  histórico do shell nem em `ps aux`.
- **Nenhum segredo é logado, salvo em disco fora do relatório, ou incluído
  em mensagens de erro.** O token de sessão vive só em memória, dentro da
  sessão HTTP, e some quando o processo termina.
- **Qualquer campo de resposta com nome sensível** (`password`, `token`,
  `apiKey`, `secret`, `credential`, `cpf`, `cnpj`, etc.) é **redigido** antes
  de aparecer em qualquer lugar do relatório.
- **Nenhum endpoint que modifica estado é chamado automaticamente** — deploy
  de bot, parar/pausar execução, criar credencial, habilitar/desabilitar
  agendamento e qualquer outra ação só são **documentados**, nunca
  executados por esta ferramenta.
- **`output/` está no `.gitignore` de propósito.** Os relatórios gerados
  contra uma Control Room real contêm dados de produção (mesmo truncados e
  parcialmente redigidos) e **nunca devem ser commitados** neste
  repositório público. O relatório de exemplo em `examples/sample_report.md`
  usa **só dados fictícios** (`--mock`), gerado sem nenhuma conexão real —
  esse sim pode ficar versionado.
- **Os gráficos de exemplo nunca guardam registro individual.** A amostra
  maior buscada só para alimentar um gráfico (`--chart-sample-size`) é
  contada/agregada em memória e descartada imediatamente — só a contagem
  final (ex.: "30 COMPLETED, 10 RUN_FAILED") entra no relatório.
- O desenho de transporte (resolução de proxy, decisão de quando desligar a
  verificação de TLS) foi baseado em uma lógica de conexão já validada em
  produção contra uma Control Room real (ver `shared_config.py`). O proxy
  padrão e o caminho de config compartilhado replicam de propósito os mesmos
  valores já usados pelo painel principal (projeto irmão) — eles já são
  públicos nesse outro repositório, não é informação nova sendo exposta
  aqui.

## Estrutura do catálogo de endpoints

`aa_doc_generator/catalog.py` descreve cada chamada como um `Endpoint`
(categoria, método, caminho, se é segura para chamar automaticamente, se é
uma ação). Os marcados com `confirmed=True` foram validados contra uma
Control Room real por outro projeto; os demais seguem o desenho conhecido da
API da Automation Anywhere, mas **podem variar por versão do Control Room**
— o relatório sempre mostra o que a sua respondeu de verdade; use o restante
como ponto de partida, não como garantia.

Para adicionar um novo endpoint ao catálogo, adicione uma entrada em
`ENDPOINTS` com os campos relevantes — o gerador de relatório, o
introspector de schema e o gerador de snippet Python funcionam para
qualquer endpoint novo sem alteração.

## Licença

MIT — ver [LICENSE](LICENSE).
