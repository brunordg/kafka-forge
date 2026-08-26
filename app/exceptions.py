class KafkaForgeError(Exception):
    """Base de toda exceção de domínio do KafkaForge (FR-026)."""

    def __init__(self, friendly_message: str, technical_detail: str = "") -> None:
        super().__init__(friendly_message)
        self.friendly_message = friendly_message
        self.technical_detail = technical_detail


class KafkaConnectionError(KafkaForgeError):
    pass


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


class KafkaAuthorizationError(KafkaForgeError):
    pass


class SchemaRegistryError(KafkaForgeError):
    pass


class AvroSchemaError(KafkaForgeError):
    """Falha de estrutura de um schema Avro carregado via `.avsc` (US-002a,
    FR-009): JSON sintaticamente válido, mas semanticamente inválido como
    schema Avro (tipo desconhecido, `record` incompleto etc.). Levantada
    exclusivamente por `avro/schema_loader.py` — nunca reconstruída ou
    duplicada em `ui/` ou `api/`, que apenas capturam e exibem
    `friendly_message`/`technical_detail`."""


class AvroValidationError(KafkaForgeError):
    """Falha de validação de um payload JSON contra um schema Avro
    (US-003a). Além de `friendly_message`/`technical_detail`, carrega o
    detalhe estruturado exigido por FR-013: o campo problemático, o tipo
    esperado e o tipo recebido — para que `ui/`/`api/` possam apontar
    exatamente o que está incorreto, em vez de uma mensagem genérica de
    validação."""

    def __init__(
        self,
        friendly_message: str,
        technical_detail: str = "",
        *,
        campo: str | None = None,
        tipo_esperado: str | None = None,
        tipo_recebido: str | None = None,
    ) -> None:
        super().__init__(friendly_message, technical_detail)
        self.campo = campo
        self.tipo_esperado = tipo_esperado
        self.tipo_recebido = tipo_recebido

    @classmethod
    def field_type_mismatch(
        cls,
        campo: str,
        tipo_esperado: str,
        tipo_recebido: str,
        technical_detail: str = "",
    ) -> "AvroValidationError":
        """FR-013 / cenário 2 de US-003a: aponta qual campo está
        incorreto, o tipo esperado e o tipo recebido, em vez de deixar o
        desenvolvedor adivinhar a partir de um erro genérico."""
        return cls(
            f"O campo '{campo}' está incorreto: era esperado o tipo "
            f"'{tipo_esperado}', mas foi recebido '{tipo_recebido}'.",
            technical_detail,
            campo=campo,
            tipo_esperado=tipo_esperado,
            tipo_recebido=tipo_recebido,
        )


class MessageSerializationError(KafkaForgeError):
    pass


class MessagePublishError(KafkaForgeError):
    pass


class ConfigurationAlreadyExistsError(KafkaForgeError):
    pass


class ConfigurationNotFoundError(KafkaForgeError):
    pass


class SchemaNotFoundError(KafkaForgeError):
    pass


class KnowledgeBaseError(KafkaForgeError):
    """Base de toda exceção do módulo `knowledge_base/` (RAG). Análoga a
    `KafkaForgeError` para o domínio Kafka: mensagens amigáveis para
    `ui/`/`api/`, detalhe técnico para logs."""


class KnowledgeBaseDisabledError(KnowledgeBaseError):
    pass


class DocumentNotFoundError(KnowledgeBaseError):
    pass


class UnsupportedDocumentTypeError(KnowledgeBaseError):
    pass


class DocumentTooLargeError(KnowledgeBaseError):
    pass


class EmbeddingProviderError(KnowledgeBaseError):
    pass


class LLMProviderError(KnowledgeBaseError):
    pass


class LLMNotConfiguredError(LLMProviderError):
    pass
