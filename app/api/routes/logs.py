from fastapi import APIRouter

from app.api.schemas.logs import OperationRecordResponse
from app.services import kafka_service
from app.services.operation_log import OperationResult, OperationType

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("", response_model=list[OperationRecordResponse])
def list_logs(tipo: OperationType | None = None, resultado: OperationResult | None = None) -> list[OperationRecordResponse]:
    """TASK-057: expõe o mesmo histórico de operações da tela de Logs para
    consumo por automação (aditiva — nenhuma outra story depende dela)."""
    records = kafka_service.list_recent_operations(tipo=tipo, resultado=resultado)
    return [OperationRecordResponse.from_domain(record) for record in records]
