---
task: TASK-010
story: N/A (fundação; pré-requisito direto de US-007a e US-007b)
status: done
---

# TASK-010 — Módulo de log estruturado de operações

## O que foi feito

Criado `app/services/operation_log.py` com o log estruturado de
operações com rotação diária descrito na decisão Q4 (seção 7 do
`plan.md`) e no modelo "Registro de Operação" (seção 5).

```python
class OperationType(str, Enum):
    TESTE_CONEXAO = "teste_conexao"
    TESTE_SCHEMA_REGISTRY = "teste_schema_registry"
    VALIDACAO_SCHEMA = "validacao_schema"
    VALIDACAO_PAYLOAD = "validacao_payload"
    PUBLICACAO = "publicacao"


class OperationResult(str, Enum):
    SUCESSO = "sucesso"
    ERRO = "erro"


class OperationRecord(BaseModel):
    timestamp: datetime
    tipo_operacao: OperationType
    resultado: OperationResult
    duracao_ms: int
    configuracao: str | None = None
    topic: str | None = None
    schema_: str | None = Field(default=None, alias="schema")
    partition: int | None = None
    offset: int | None = None
    key: str | None = None
    erro_tecnico: str | None = None


def append_operation_record(tipo_operacao, resultado, duracao_ms, *, ...) -> OperationRecord: ...
def read_operations_for_date(target_date: date) -> list[OperationRecord]: ...
def read_recent_operations(limit: int | None = None, days: int = 7) -> list[OperationRecord]: ...
```

Decisões de implementação:

- **Formato `.jsonl` (JSON Lines), não um array `.json` único.** A seção
  9/10.1 do plano ilustra o nome do arquivo como `.json`, mas o texto
  desta tarefa permite explicitamente `.json` "ou `.jsonl`". Escolhi
  `.jsonl` porque o requisito central da DoD é *anexar* sem
  reescrever/sobrescrever: com um array JSON único, cada gravação exigiria
  ler o arquivo inteiro do dia, desserializar, acrescentar e regravar por
  completo — O(n) por escrita e um `write` incompleto no meio desse
  processo corrompe o dia inteiro. Com JSON Lines, cada gravação é um
  `open(..., "a")` + uma linha + `\n` — O(1), e uma interrupção abrupta do
  processo só arrisca truncar a **última** linha, nunca o histórico
  anterior. A função de leitura já descarta silenciosamente uma linha
  malformada (`_parse_lines`), então mesmo esse pior caso não derruba a
  leitura do resto do dia.
- **Nome de arquivo por dia da operação, não do momento da leitura**:
  `_log_file_for_date` deriva o nome (`operacoes-AAAA-MM-DD.jsonl`) a
  partir de `record.timestamp.date()`. `append_operation_record` aceita
  `timestamp` como parâmetro opcional (default `datetime.now(timezone.utc)`)
  — essencial para os testes serem determinísticos, e também é o encaixe
  natural para reprocessamento futuro, se necessário.
- **Campo `schema` via `Field(alias="schema")` sobre o atributo Python
  `schema_`.** Testei isoladamente: nomear o campo Pydantic diretamente
  `schema` funciona, mas emite `UserWarning: Field name "schema" ...
  shadows an attribute in parent "BaseModel"` (conflito com o método
  `BaseModel.schema()`, mantido por compatibilidade com Pydantic v1).
  Usar `schema_` como nome do atributo + `alias="schema"` elimina o aviso
  (confirmado rodando com `warnings.simplefilter("error")`) e mantém a
  chave JSON persistida idêntica ao nome do campo na tabela "Registro de
  Operação" da seção 5 do plano — `model_dump_json(by_alias=True)` na
  escrita, `model_validate_json` (que já casa pelo alias) na leitura.
- **Permissão `0600` também nos arquivos de log**, não só no diretório
  `logs/` (que já vinha `0700` da TASK-006). Isso não estava
  explicitamente pedido na Definition of Done desta tarefa, mas é uma
  consequência direta do mesmo risco de segurança da seção 11 do plano
  que já motivou a TASK-006 ("mitigar apenas com permissões de arquivo
  restritas, ex.: 0600, no diretório `~/.kafkaforge/`") — sem esse
  `os.chmod` explícito, cada `operacoes-AAAA-MM-DD.jsonl` nasceria com o
  modo padrão do `umask` do processo (tipicamente `644`, legível por
  qualquer usuário da máquina), já que `erro_tecnico` pode conter detalhes
  técnicos sensíveis (hosts, mensagens de exceção de bibliotecas
  externas). Reaproveitei a constante `FILE_MODE` já definida em
  `app/config/storage.py` (TASK-006) em vez de duplicar o valor `0o600`.
- **`read_operations_for_date`** cobre a leitura de um dia específico
  (base direta para o Dashboard/Logs olharem "hoje"); **
  `read_recent_operations(limit, days)`** lista os arquivos de `logs/`
  mais recentes (ordenação lexicográfica das datas no nome do arquivo,
  que já é cronológica por construção — sem índice nem banco de dados,
  conforme a DoD), lê-os do mais novo ao mais antigo, e ordena os
  registros agregados por `timestamp` decrescente — usado pelas
  TASK-054 (Dashboard) e TASK-056 (tela de Logs).

## Verificação

- `tests/test_operation_log.py` (novo), 13 casos, cobrindo diretamente os
  três itens da Definition o Done:
  - **Cria/anexa ao arquivo do dia corrente sem sobrescrever dias
    anteriores**: `test_append_creates_file_named_after_the_operation_day`,
    `test_multiple_appends_on_the_same_day_accumulate_without_overwriting`,
    `test_appends_on_different_days_do_not_touch_previous_days_file`.
  - **Campos mínimos de FR-024 presentes**:
    `test_append_record_contains_all_fr024_minimum_fields` (timestamp,
    tipo_operacao, configuracao, topic/schema, resultado, duracao_ms,
    erro_tecnico) e
    `test_append_record_stores_partition_offset_and_key_when_applicable`
    (partition/offset/key quando aplicável).
  - **Leitura do(s) arquivo(s) mais recente(s) sem índice/banco de
    dados**: `test_read_recent_operations_orders_newest_first_across_days`,
    `test_read_recent_operations_respects_limit`,
    `test_read_recent_operations_ignores_files_older_than_days_window`.
  - Casos adicionais: arquivo ausente retorna lista vazia, timestamp
    default usa o relógio atual, permissão `0600` do arquivo de log, e
    resiliência a uma última linha corrompida
    (`test_read_operations_skips_a_corrupted_trailing_line`).
- `pytest -v -W error` (venv limpo, avisos tratados como erro): **68
  testes, todos `PASSED`** (13 novos + 55 já existentes das
  TASK-005 a TASK-009 — nenhuma regressão, e nenhum `UserWarning` de
  shadowing do Pydantic escapou).
- `grep` confirma que `app/services/operation_log.py` não importa nada de
  `ui`, `api`, `kafka`, `avro` ou `registry`.
- Ambiente virtual de teste e caches removidos após a validação.

## Checklist

- [x] Unit tests pass — 68/68 (13 novos em `tests/test_operation_log.py`)
- [ ] Integration tests pass — N/A, módulo só depende do sistema de arquivos local
- [ ] Typecheck passes — N/A, projeto ainda não tem configuração de typecheck
- [ ] Linter passes — N/A, projeto ainda não tem linter configurado

## Próximos passos

TASK-011 (rota `GET /api/v1/health` + registro de rotas em `main.py`),
que fecha a Fase 2 — Fundação. `append_operation_record` passa a ser
chamado de verdade a partir da TASK-017 (`test_connection`), TASK-028
(`validate_payload`) e TASK-034 (`publish`) em diante, e
`read_recent_operations`/`read_operations_for_date` serão consumidos
pela TASK-053/TASK-054 (Dashboard) e TASK-056 (tela de Logs).
