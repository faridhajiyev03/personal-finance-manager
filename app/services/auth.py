from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserCreate, UserLogin
from app.security import hash_password, verify_password


class EmailAlreadyExistsError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


def get_user_by_email(email: str, db: Session) -> User | None:
    stmt = select(User).where(User.email == email)
    return db.execute(stmt).scalars().first()


def register_user(data: UserCreate, db: Session) -> User:
    email = str(data.email).lower()

    if get_user_by_email(email, db) is not None:
        raise EmailAlreadyExistsError()

    user = User(
        email=email,
        hashed_password=hash_password(data.password),
    )

    try:
        db.add(user)
        db.commit()
    except IntegrityError:
        db.rollback()

        # Другой запрос мог зарегистрировать этот email
        # между нашей проверкой и сохранением.
        if get_user_by_email(email, db) is not None:
            raise EmailAlreadyExistsError()

        raise

    db.refresh(user)
    return user


def authenticate_user(data: UserLogin, db: Session) -> User:
    email = str(data.email).lower()
    user = get_user_by_email(email, db)

    if user is None:
        raise InvalidCredentialsError()

    if not verify_password(data.password, user.hashed_password):
        raise InvalidCredentialsError()

    return user