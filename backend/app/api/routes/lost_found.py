"""The Lost & Found community board.

Reports are readable by any signed-in traveller — reuniting people with their
property is the whole point — but a row is owned by whoever filed it, and
ownership is taken from the session rather than the request.
"""
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.lost_found import LostFoundReport
from app.models.user import User
from app.schemas.lost_found import LostFoundCreate, LostFoundResponse
from app.services.lost_found_media import (
    InvalidImageError,
    delete_stored_image,
    save_data_url,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/lost-found", tags=["lost-found"])

# Enough for a busy board without returning an unbounded result set.
_MAX_REPORTS = 200


def _to_response(report: LostFoundReport, current_user_id: UUID) -> LostFoundResponse:
    payload = LostFoundResponse.model_validate(report)
    payload.is_mine = report.user_id == current_user_id
    return payload


@router.get("", response_model=list[LostFoundResponse])
def list_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[LostFoundResponse]:
    """Every traveller's reports, newest first — this is a shared board."""
    reports = (
        db.query(LostFoundReport)
        .order_by(LostFoundReport.created_at.desc())
        .limit(_MAX_REPORTS)
        .all()
    )
    return [_to_response(report, current_user.id) for report in reports]


@router.post("", response_model=LostFoundResponse, status_code=status.HTTP_201_CREATED)
def create_report(
    payload: LostFoundCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LostFoundResponse:
    """File a report against the signed-in account."""
    image_url: str | None = None
    if payload.image_data_url:
        try:
            # Written before the transaction opens: a rejected image should
            # fail the request outright, not roll back a half-made row.
            image_url = save_data_url(payload.image_data_url)
        except InvalidImageError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    report = LostFoundReport(
        user_id=current_user.id,
        title=payload.title.strip(),
        report_type=payload.report_type,
        category=payload.category.strip(),
        location=payload.location.strip(),
        reported_date=payload.reported_date,
        description=payload.description.strip(),
        image_url=image_url,
        contact=payload.contact.strip(),
        status="Open",
    )

    # Authentication already opened a transaction; close it so the insert runs
    # in a single explicit one, matching the planner's persistence pattern.
    db.rollback()
    try:
        with db.begin():
            db.add(report)
    except Exception:
        # Don't leave an orphaned file behind if the row never landed.
        delete_stored_image(image_url)
        raise

    db.refresh(report)
    return _to_response(report, current_user.id)


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(
    report_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Withdraw your own report.

    Someone else's report returns 404 rather than 403: confirming the id
    exists would leak that another traveller filed it.
    """
    report = (
        db.query(LostFoundReport)
        .filter(LostFoundReport.id == report_id, LostFoundReport.user_id == current_user.id)
        .first()
    )
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    image_url = report.image_url
    db.rollback()
    with db.begin():
        db.delete(report)
    delete_stored_image(image_url)
