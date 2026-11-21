from datetime import date
from decimal import Decimal
from typing import Literal

from sqlalchemy import case, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.schemas.transaction import (
    TransactionCreate,
    TransactionUpdate,
)


class TransactionNotFoundError(Exception):
    pass


def get_transaction(
    transaction_id: int,
    db: Session,
    current_user_id: int,
) -> Transaction:
    # Another user's transaction is reported as "not found" (not "forbidden"),
    # so the API does not reveal which transaction IDs exist.
    stmt = select(Transaction).where(
        Transaction.id == transaction_id,
        Transaction.user_id == current_user_id,
    )
    transaction = db.execute(stmt).scalars().first()

    if transaction is None:
        raise TransactionNotFoundError()

    return transaction


def create_transaction(
    data: TransactionCreate,
    db: Session,
    current_user_id: int,
) -> Transaction:
    transaction = Transaction(
        **data.model_dump(),
        user_id=current_user_id,
    )

    try:
        db.add(transaction)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise

    db.refresh(transaction)
    return transaction


def list_transactions(
    db: Session,
    current_user_id: int,
    transaction_type: Literal["income", "expense"] | None = None,
    category: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Transaction], int]:
    stmt = select(Transaction).where(
        Transaction.user_id == current_user_id
    )

    if transaction_type is not None:
        stmt = stmt.where(Transaction.type == transaction_type)

    if category is not None:
        stmt = stmt.where(Transaction.category == category)

    if date_from is not None:
        stmt = stmt.where(Transaction.date >= date_from)

    if date_to is not None:
        stmt = stmt.where(Transaction.date <= date_to)

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))

    stmt = (
        stmt
        .order_by(Transaction.date.desc(), Transaction.id.desc())
        .limit(limit)
        .offset(offset)
    )

    return list(db.execute(stmt).scalars().all()), total


def update_transaction(
    transaction_id: int,
    data: TransactionUpdate,
    db: Session,
    current_user_id: int,
) -> Transaction:
    transaction = get_transaction(
        transaction_id,
        db,
        current_user_id,
    )

    try:
        for field, value in data.model_dump(
            exclude_unset=True
        ).items():
            setattr(transaction, field, value)

        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise

    db.refresh(transaction)
    return transaction


def delete_transaction(
    transaction_id: int,
    db: Session,
    current_user_id: int,
) -> None:
    transaction = get_transaction(
        transaction_id,
        db,
        current_user_id,
    )

    try:
        db.delete(transaction)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise


def get_summary(
    db: Session,
    current_user_id: int,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict:
    stmt = select(
        func.coalesce(
            func.sum(
                case(
                    (
                        Transaction.type == "income",
                        Transaction.amount,
                    ),
                    else_=Decimal("0.00"),
                )
            ),
            Decimal("0.00"),
        ).label("income"),
        func.coalesce(
            func.sum(
                case(
                    (
                        Transaction.type == "expense",
                        Transaction.amount,
                    ),
                    else_=Decimal("0.00"),
                )
            ),
            Decimal("0.00"),
        ).label("expense"),
    ).where(
        Transaction.user_id == current_user_id
    )

    if date_from is not None:
        stmt = stmt.where(Transaction.date >= date_from)

    if date_to is not None:
        stmt = stmt.where(Transaction.date <= date_to)

    result = db.execute(stmt).one()

    return {
        "income": result.income,
        "expense": result.expense,
        "balance": result.income - result.expense,
    }