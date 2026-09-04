from __future__ import annotations

from typing import Any

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    status,
)

from backend.app.services.dashboard_service import (
    DashboardDataError,
    DashboardItemNotFoundError,
    DashboardService,
)


router = APIRouter(
    prefix="/api/dashboard",
    tags=["dashboard"],
)


def _service() -> DashboardService:
    return DashboardService()


def _raise_data_error(
    exc: DashboardDataError,
) -> None:
    raise HTTPException(
        status_code=(
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ),
        detail=str(
            exc
        ),
    ) from exc


@router.get(
    "/summary"
)
def get_dashboard_summary() -> dict[str, Any]:
    try:
        return (
            _service()
            .get_summary()
        )

    except DashboardDataError as exc:
        _raise_data_error(
            exc
        )


@router.get(
    "/benchmark"
)
def get_dashboard_benchmark() -> dict[str, Any]:
    try:
        return (
            _service()
            .get_benchmark()
        )

    except DashboardDataError as exc:
        _raise_data_error(
            exc
        )


@router.get(
    "/exceptions"
)
def get_dashboard_exceptions() -> dict[str, Any]:
    try:
        return (
            _service()
            .get_exceptions()
        )

    except DashboardDataError as exc:
        _raise_data_error(
            exc
        )


@router.get(
    "/high-value-exceptions"
)
def get_high_value_exceptions(
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
    ),
) -> dict[str, Any]:
    try:
        return (
            _service()
            .get_high_value_exceptions(
                limit=limit
            )
        )

    except DashboardDataError as exc:
        _raise_data_error(
            exc
        )


@router.get(
    "/exceptions/{transaction_id}"
)
def get_exception_detail(
    transaction_id: str,
) -> dict[str, Any]:
    try:
        return (
            _service()
            .get_exception_detail(
                transaction_id=transaction_id,
            )
        )

    except DashboardItemNotFoundError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=str(
                exc
            ),
        ) from exc

    except DashboardDataError as exc:
        _raise_data_error(
            exc
        )


@router.get(
    "/audit"
)
def get_dashboard_audit() -> dict[str, Any]:
    try:
        return (
            _service()
            .get_audit_status()
        )

    except DashboardDataError as exc:
        _raise_data_error(
            exc
        )


@router.get(
    "/razorpay"
)
def get_dashboard_razorpay() -> dict[str, Any]:
    try:
        return (
            _service()
            .get_razorpay_status()
        )

    except DashboardDataError as exc:
        _raise_data_error(
            exc
        )