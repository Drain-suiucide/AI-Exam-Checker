"""Public exam-configuration catalogue."""

from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status

from app.config import settings
from app.schemas.configurations import ConfigurationListResponse
from app.services.configuration_catalog import demo_configurations

router = APIRouter(prefix="/exam-configurations", tags=["exam-configurations"])


@router.get("", response_model=ConfigurationListResponse)
async def list_exam_configurations(
    configuration_status: Literal["approved", "draft", "all"] = Query("approved", alias="status"),
) -> ConfigurationListResponse:
    """List configurations available for creating a submission."""
    if configuration_status != "approved" and not settings.ALLOW_UNAPPROVED_CONFIG:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ к неподтверждённым конфигурациям запрещён.",
            headers={"X-Error-Code": "FORBIDDEN"},
        )

    items = demo_configurations()
    if configuration_status != "all":
        items = [item for item in items if item.status == configuration_status]
    items.sort(key=lambda item: (not item.is_default, -item.created_at.timestamp()))
    return ConfigurationListResponse(items=items)
