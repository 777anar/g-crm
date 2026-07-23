import csv
import io
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from core.api.errors import BusinessRuleViolationError
from core.api.pagination import decode_cursor, encode_cursor
from core.audit.models import AuditLog, AuditRetentionPolicy
from core.audit.schemas import (
    AuditLogListOut,
    AuditLogOut,
    RetentionPolicyOut,
    RetentionPolicyUpdate,
    RetentionPurgeOut,
)
from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission

router = APIRouter(prefix="/api/v1/audit", tags=["core:audit"])

# A single permission gates the whole compliance surface (list, export,
# retention policy, purge): this is company-wide audit history across every
# module, not a per-module read -- deliberately owner-only (the "export"
# action suffix falls through core/rbac/permissions.py's default rank,
# ROLE_OWNER, same as any unrecognized action).
_PERMISSION = "core:audit:export"


def _apply_filters(
    stmt,
    *,
    company_id: uuid.UUID,
    module: Optional[str],
    entity_type: Optional[str],
    action: Optional[str],
    actor_user_id: Optional[uuid.UUID],
    date_from: Optional[datetime],
    date_to: Optional[datetime],
):
    stmt = stmt.where(AuditLog.company_id == company_id)
    if module:
        stmt = stmt.where(AuditLog.module == module)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if actor_user_id:
        stmt = stmt.where(AuditLog.actor_user_id == actor_user_id)
    if date_from:
        stmt = stmt.where(AuditLog.created_at >= date_from)
    if date_to:
        stmt = stmt.where(AuditLog.created_at <= date_to)
    return stmt


@router.get("/logs", response_model=AuditLogListOut)
def list_audit_logs(
    module: Optional[str] = Query(default=None),
    entity_type: Optional[str] = Query(default=None),
    action: Optional[str] = Query(default=None),
    actor_user_id: Optional[uuid.UUID] = Query(default=None),
    date_from: Optional[datetime] = Query(default=None),
    date_to: Optional[datetime] = Query(default=None),
    limit: int = Query(default=50, le=200),
    cursor: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission(_PERMISSION)),
) -> AuditLogListOut:
    offset = decode_cursor(cursor)
    stmt = _apply_filters(
        select(AuditLog),
        company_id=current_user.active_company_id,
        module=module,
        entity_type=entity_type,
        action=action,
        actor_user_id=actor_user_id,
        date_from=date_from,
        date_to=date_to,
    ).order_by(AuditLog.created_at.desc()).offset(offset).limit(limit + 1)
    rows = db.execute(stmt).scalars().all()
    has_more = len(rows) > limit
    page = rows[:limit]
    next_cursor = encode_cursor(offset=offset + limit) if has_more else None
    return AuditLogListOut(items=[AuditLogOut.model_validate(r) for r in page], next_cursor=next_cursor)


_EXPORT_LIMIT = 50_000
_CSV_HEADER = ["id", "created_at", "module", "actor_user_id", "action", "entity_type", "entity_id", "diff_json"]


@router.get("/logs/export")
def export_audit_logs(
    module: Optional[str] = Query(default=None),
    entity_type: Optional[str] = Query(default=None),
    action: Optional[str] = Query(default=None),
    actor_user_id: Optional[uuid.UUID] = Query(default=None),
    date_from: Optional[datetime] = Query(default=None),
    date_to: Optional[datetime] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission(_PERMISSION)),
) -> Response:
    stmt = _apply_filters(
        select(AuditLog),
        company_id=current_user.active_company_id,
        module=module,
        entity_type=entity_type,
        action=action,
        actor_user_id=actor_user_id,
        date_from=date_from,
        date_to=date_to,
    ).order_by(AuditLog.created_at.desc()).limit(_EXPORT_LIMIT)
    rows = db.execute(stmt).scalars().all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(_CSV_HEADER)
    for row in rows:
        writer.writerow(
            [
                str(row.id),
                row.created_at.isoformat() if row.created_at else "",
                row.module,
                str(row.actor_user_id),
                row.action,
                row.entity_type,
                str(row.entity_id),
                str(row.diff_json) if row.diff_json else "",
            ]
        )
    # Leading BOM so Excel (the realistic destination for a compliance
    # export) detects UTF-8 instead of mangling non-Latin text.
    content = ("﻿" + buffer.getvalue()).encode("utf-8")
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="audit_log_export.csv"'},
    )


def _get_or_create_policy(db: Session, company_id: uuid.UUID, actor_user_id: uuid.UUID) -> AuditRetentionPolicy:
    policy = db.scalar(select(AuditRetentionPolicy).where(AuditRetentionPolicy.company_id == company_id))
    if policy is None:
        policy = AuditRetentionPolicy(company_id=company_id, retention_days=None, updated_by=actor_user_id)
        db.add(policy)
        db.flush()
    return policy


@router.get("/retention-policy", response_model=RetentionPolicyOut)
def get_retention_policy(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission(_PERMISSION)),
) -> RetentionPolicyOut:
    policy = db.scalar(
        select(AuditRetentionPolicy).where(AuditRetentionPolicy.company_id == current_user.active_company_id)
    )
    if policy is None:
        return RetentionPolicyOut(retention_days=None, updated_at=None)
    return RetentionPolicyOut(retention_days=policy.retention_days, updated_at=policy.updated_at)


@router.put("/retention-policy", response_model=RetentionPolicyOut)
def set_retention_policy(
    payload: RetentionPolicyUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission(_PERMISSION)),
) -> RetentionPolicyOut:
    policy = _get_or_create_policy(db, current_user.active_company_id, current_user.user_id)
    policy.retention_days = payload.retention_days
    policy.updated_by = current_user.user_id
    db.commit()
    db.refresh(policy)
    return RetentionPolicyOut(retention_days=policy.retention_days, updated_at=policy.updated_at)


@router.post("/retention-policy/purge", response_model=RetentionPurgeOut)
def purge_expired_audit_logs(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission(_PERMISSION)),
) -> RetentionPurgeOut:
    """Manually deletes audit_log rows older than the configured retention
    window. Deliberately not automatic (no background job queue exists yet
    -- see MASTER_DEVELOPMENT_ROADMAP.md Phase 24); an owner runs this
    on-demand from the retention policy admin screen."""
    policy = db.scalar(
        select(AuditRetentionPolicy).where(AuditRetentionPolicy.company_id == current_user.active_company_id)
    )
    if policy is None or policy.retention_days is None:
        raise BusinessRuleViolationError("No retention policy configured -- set retention_days first")
    cutoff = datetime.now(timezone.utc) - timedelta(days=policy.retention_days)
    result = db.execute(
        delete(AuditLog).where(AuditLog.company_id == current_user.active_company_id, AuditLog.created_at < cutoff)
    )
    db.commit()
    return RetentionPurgeOut(deleted_count=result.rowcount or 0)
