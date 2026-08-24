---
task: TASK-016
story: US-001b
status: done
---

# TASK-016 — Comportamento específico de `KafkaAuthenticationError`

## O que foi feito

Estendido `app/exceptions.py` com um construtor nomeado
(`classmethod`) em `KafkaAuthenticationError`, específico para o cenário
3 de US-001b (certificado de cliente cuja chave privada exige senha, mas
`client_key_password` não foi informado), e `app/kafka/connection.py`
(TASK-015) foi atualizado para usá-lo em vez de compor a mensagem
amigável inline.

```python
class KafkaAuthenticationError(KafkaForgeError):
    @classmethod
    def missing_client_key_password(cls, technical_detail: str = "") -> "KafkaAuthenticationError":
        """Cenário 3 de US-001b: certificado de cliente cuja chave privada
        exige senha, mas `client_key_password` não foi informado. Aponta
        esse campo especificamente, em vez de um erro genérico de SSL."""
        return cls(
            "A chave privada do cliente está protegida por senha, mas o "
            "campo client_key_password não foi informado.",
            technical_detail,
        )
```

```python
# app/kafka/connection.py — antes construía a mensagem inline, agora:
raise KafkaAuthenticationError.missing_client_key_password(
    "PEM de client_key contém um cabeçalho de chave criptografada "
    "(ENCRYPTED PRIVATE KEY ou Proc-Type: 4,ENCRYPTED) e "
    "client_key_password está vazio."
)
```

Decisões de implementação:

- **Construtor nomeado (`classmethod`) em vez de uma subclasse nova.** A
  tarefa pede para "estender `app/exceptions.py` com o comportamento
  específico de `KafkaAuthenticationError`" — não para criar um novo tipo
  de exceção. `KafkaAuthenticationError` continua sendo o único tipo
  levantado para qualquer falha de autenticação Kafka (útil para quem
  captura por tipo, ex.: `except KafkaAuthenticationError:`), mas ganha um
  construtor específico (`missing_client_key_password`) que centraliza,
  num único lugar, a mensagem amigável exata deste cenário — em vez de
  cada chamador (hoje só `connection.py`, mas potencialmente outros no
  futuro) ter que lembrar de escrever/manter essa frase.
- **Mensagem fixa, só o detalhe técnico é parametrizável.** A mensagem
  amigável menciona `client_key_password` explicitamente (satisfaz a DoD
  ao pé da letra) e não contém a palavra "SSL" isolada (a DoD original do
  plano pede explicitamente para não ser "um erro genérico de SSL" —
  testado literalmente). O detalhe técnico bruto continua sendo passado
  pelo chamador, já que só ele sabe o contexto exato (qual cabeçalho PEM
  disparou a checagem, por exemplo).
- **`app/kafka/connection.py` (TASK-015) atualizado para consumir este
  construtor** em vez da mensagem que antes estava duplicada ali —
  elimina a duplicação e deixa `app/exceptions.py` como a única fonte da
  verdade para o texto exato desta mensagem, coerente com o papel do
  módulo descrito na seção 8 do plano.

## Verificação

- **`tests/test_exceptions.py`** (estendido), 5 casos novos, cobrindo o
  cenário **isoladamente** — nenhum deles importa `app.kafka.connection`,
  `confluent_kafka` ou qualquer coisa relacionada a broker:
  - `missing_client_key_password()` retorna de fato uma
    `KafkaAuthenticationError`.
  - A mensagem amigável contém `client_key_password` e não contém "SSL"
    (garante que não é um erro genérico de SSL sem contexto).
  - O detalhe técnico informado é preservado; o default é `""`.
  - A exceção pode ser levantada e capturada normalmente com
    `pytest.raises`.
- `pytest -v` em `tests/test_exceptions.py`: **22 testes, todos
  `PASSED`** (5 novos + 17 já existentes da TASK-005).
- `pytest -q` na suíte completa (venv limpo, `requirements-dev.txt`):
  **133 testes, todos `PASSED`** (5 novos + 128 já existentes — inclui a
  reexecução de `tests/test_kafka_connection.py`, confirmando que a
  refatoração do construtor da mensagem em `connection.py` não quebrou
  nada da TASK-015).
- `grep` confirma que `app/exceptions.py` continua sem nenhuma
  dependência de `ui`, `api`, `kafka`, `avro` ou `registry`.
- Ambiente virtual de teste e caches removidos após a validação.

## Checklist

- [x] Unit tests pass — 133/133 (5 novos em `tests/test_exceptions.py`)
- [ ] Integration tests pass — N/A, exceção pura, sem dependência de rede/broker (exigência explícita da própria DoD)
- [ ] Typecheck passes — N/A, projeto ainda não tem configuração de typecheck
- [ ] Linter passes — N/A, projeto ainda não tem linter configurado

## Próximos passos

TASK-017 (`services/kafka_service.test_connection`, implementação real
sobre `kafka/connection.py` da TASK-015), que deve continuar propagando
`KafkaAuthenticationError` (agora também via este construtor nomeado)
até a UI/API sem perder a mensagem específica.
