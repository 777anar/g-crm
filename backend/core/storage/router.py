import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from core.api.errors import NotFoundError, ValidationAPIError
from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, get_current_user, require_permission
from core.storage.client import new_storage_key, storage_client
from core.storage.models import Document
from core.storage.schemas import DocumentOut, SignedUrlOut

router = APIRouter(prefix="/api/v1/core/documents", tags=["core:documents"])

MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post("", response_model=DocumentOut)
async def upload_document(
    module: str = Form(...),
    related_entity_type: str = Form(...),
    related_entity_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    # "write" actions require at least rep-tier per the generic action-suffix
    # RBAC convention -- this is a core (not module-specific) permission name
    # precisely because the core endpoint doesn't know which business module
    # the upload is "for" until the form body is parsed.
    current_user: CurrentUser = Depends(require_permission("core:documents:write")),
) -> DocumentOut:
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise ValidationAPIError(
            f"File exceeds the maximum upload size of {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} MB",
            details=[{"field": "file", "issue": "file too large"}],
        )

    key = new_storage_key(current_user.active_company_id, module, file.filename)
    storage_client.upload(key=key, content=content, mime_type=file.content_type or "application/octet-stream")

    document = Document(
        company_id=current_user.active_company_id,
        module=module,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        storage_path=key,
        mime_type=file.content_type or "application/octet-stream",
        uploaded_by=current_user.user_id,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return DocumentOut(id=document.id, storage_path=document.storage_path, mime_type=document.mime_type)


@router.get("/{document_id}", response_model=SignedUrlOut)
def get_document_url(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> SignedUrlOut:
    document = db.get(Document, document_id)
    if document is None or document.company_id != current_user.active_company_id:
        raise NotFoundError("Document not found")
    url = storage_client.get_signed_url(key=document.storage_path)
    return SignedUrlOut(url=url)
