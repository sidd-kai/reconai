from __future__ import annotations

from typing import Any

from fastapi import (
    APIRouter,
    HTTPException,
    status,
)

from backend.app.services.razorpay_demo_service import (
    RazorpayDemoError,
    RazorpayDemoService,
    serialize_razorpay_demo_result,
)


router = APIRouter(
    prefix="/api/demo/razorpay",
    tags=["razorpay-demo"],
)


@router.post(
    "/reconcile"
)
def run_razorpay_demo() -> dict[str, Any]:
    try:
        result = (
            RazorpayDemoService()
            .run()
        )

    except RazorpayDemoError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=str(
                exc
            ),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Razorpay demo failed safely. "
                "Production benchmark artifacts were not modified. "
                f"{type(exc).__name__}: {exc}"
            ),
        ) from exc

    return (
        serialize_razorpay_demo_result(
            result
        )
    )