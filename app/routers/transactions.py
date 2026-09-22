from datetime import date
from typing import Literal

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Path,
    Query,
    Response,
)
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User

from app.security import get_current_user
from app.services import transactions as service

from app.schemas.transaction import (
    TransactionCreate,
    TransactionResponse,
    TransactionSummary,
    TransactionUpdate,
)


router = APIRouter(
    prefix="/transactions",
    tags=["Transactions"],
)


@router.post(
    "",
    response_model=TransactionResponse,
    status_code=201,
)
def create_transaction(
    data: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.create_transaction(
        data,
        db,
        current_user.id,
    )


@router.get("", response_model=list[TransactionResponse])
def list_transactions(
    transaction_type: Literal["income", "expense"] | None = Query(
        default=None,
        alias="type",
    ),
    category: str | None = Query(
        default=None,
        min_length=1,
        max_length=50,
    ),
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if (
        date_from is not None
        and date_to is not None
        and date_from > date_to
    ):
        raise HTTPException(
            status_code=422,
            detail="date_from must not be later than date_to",
        )

    return service.list_transactions(
        db=db,
        current_user_id=current_user.id,
        transaction_type=transaction_type,
        category=category,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )

@router.get("/summary", response_model=TransactionSummary)
def get_summary(
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if (
        date_from is not None
        and date_to is not None
        and date_from > date_to
    ):
        raise HTTPException(
            status_code=422,
            detail="date_from must not be later than date_to",
        )

    return service.get_summary(
        db=db,
        current_user_id=current_user.id,
        date_from=date_from,
        date_to=date_to,
    )

@router.get(
    "/{transaction_id}",
    response_model=TransactionResponse,
)
def get_transaction(
    transaction_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return service.get_transaction(
            transaction_id,
            db,
            current_user.id,
        )
    except service.TransactionNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found",
        )
    except service.TransactionPermissionError:
        raise HTTPException(
            status_code=403,
            detail="You cannot access this transaction",
        )


@router.patch(
    "/{transaction_id}",
    response_model=TransactionResponse,
)
def update_transaction(
    data: TransactionUpdate,
    transaction_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return service.update_transaction(
            transaction_id,
            data,
            db,
            current_user.id,
        )
    except service.TransactionNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found",
        )
    except service.TransactionPermissionError:
        raise HTTPException(
            status_code=403,
            detail="You cannot edit this transaction",
        )


@router.delete("/{transaction_id}", status_code=204)
def delete_transaction(
    transaction_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        service.delete_transaction(
            transaction_id,
            db,
            current_user.id,
        )
    except service.TransactionNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found",
        )
    except service.TransactionPermissionError:
        raise HTTPException(
            status_code=403,
            detail="You cannot delete this transaction",
        )

    return Response(status_code=204)