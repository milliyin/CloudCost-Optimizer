from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.api.deps import DbSession, get_current_user
from app.models.user import User
from app.services.report_service import build_csv_report, build_pdf_report

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/export")
async def export_report(
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
    format: str = Query(pattern="^(pdf|csv)$"),
) -> Response:
    if format == "csv":
        payload = await build_csv_report(db, current_user)
        return Response(
            content=payload,
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="cloudcost-report.csv"'},
        )

    payload = await build_pdf_report(db, current_user)
    return Response(
        content=payload,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="cloudcost-report.pdf"'},
    )
