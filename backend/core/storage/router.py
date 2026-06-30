import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, get_current_user
from core.storage.client import new_storage_key, storage_client
from core.storage.models import Document
from core.storage.schemas import DocumentOut, SignedUrlOut

router = APIRouter(prefix="/api/v1/core/documents", tags=["core:documents"])


@router.post("", response_model=DocumentOut)
async def upload_document(
    module: str = Form(...),
    related_entity_type: str = Form(...),
    related_entity_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> DocumentOut:
    content = await file.read()
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
