from datetime import date
from typing import Literal

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.schemas.transaction import (
    TransactionCreate,
    TransactionUpdate,
)

from decimal import Decimal
from sqlalchemy import case, func


class TransactionNotFoundError(Exception):
    pass


class TransactionPermissionError(Exception):
    pass


def get_transaction(
    transaction_id: int,
    db: Session,
    current_user_id: int,
) -> Transaction:
    transaction = db.get(Transaction, transaction_id)

    if transaction is None:
        raise TransactionNotFoundError()

    if transaction.user_id != current_user_id:
        raise TransactionPermissionError()

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
) -> list[Transaction]:
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

    stmt = (
        stmt
        .order_by(Transaction.date.desc(), Transaction.id.desc())
        .limit(limit)
        .offset(offset)
    )

    return list(db.execute(stmt).scalars().all())


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