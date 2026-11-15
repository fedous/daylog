from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    MetaData,
    Text,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    # Nomi stabili per vincoli e indici: Alembic li scrive nelle migrazioni,
    # e servono per poterli modificare o cancellare in quelle successive.
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(table_name)s_%(column_0_N_name)s",
            "uq": "uq_%(table_name)s_%(column_0_N_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )
    type_annotation_map = {
        str: Text(),
        datetime: DateTime(timezone=True),
    }


class Timestamps:
    """Campi tecnici. updated_at lo aggiorna SQLAlchemy a ogni UPDATE fatto con l'ORM."""

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class User(Timestamps, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    email: Mapped[str] = mapped_column(unique=True)


class Habit(Timestamps, Base):
    __tablename__ = "habits"
    __table_args__ = (
        # Nomi unici solo tra le abitudini attive (un nome archiviato si può riusare),
        # senza distinguere maiuscole e minuscole: "Meditare" e "meditare" sono la stessa
        Index(
            "uq_habits_user_id_name_active",
            "user_id",
            text("lower(name)"),
            unique=True,
            postgresql_where=text("archived_at IS NULL"),
        ),
        CheckConstraint("kind IN ('boolean', 'quantity')", name="kind_valid"),
        CheckConstraint("kind = 'quantity' OR unit IS NULL", name="unit_only_for_quantity"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    name: Mapped[str]
    kind: Mapped[str]
    unit: Mapped[str | None]
    position: Mapped[int]
    archived_at: Mapped[datetime | None]


class Check(Timestamps, Base):
    __tablename__ = "checks"
    __table_args__ = (CheckConstraint("value > 0", name="value_positive"),)

    habit_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("habits.id"), primary_key=True)
    day: Mapped[date] = mapped_column(primary_key=True)
    value: Mapped[int | None]


class DayNote(Timestamps, Base):
    __tablename__ = "day_notes"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), primary_key=True)
    day: Mapped[date] = mapped_column(primary_key=True)
    text: Mapped[str]
