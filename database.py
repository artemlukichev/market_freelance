"""Модуль моделей и работы с базой данных."""

from sqlalchemy import ForeignKey
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Создание движка и сессии
engine = create_async_engine("sqlite+aiosqlite:///tasks.db")
new_session = async_sessionmaker(engine, expire_on_commit=False)


class Model(DeclarativeBase):
    """Базовая модель для ORM."""
    pass


class TaskOrm(Model):
    """Модель таблицы задач."""
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    description: Mapped[str | None]
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    executor_id: Mapped[int | None] = mapped_column(ForeignKey("executors.id"))
    subject_area: Mapped[str]
    results = relationship("TaskResultOrm", back_populates="task")


class UserOrm(Model):
    """Модель таблицы пользователей."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True)
    hashed_password: Mapped[str]


class ExecutorOrm(Model):
    """Модель таблицы исполнителей."""
    __tablename__ = "executors"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True)
    specializations: Mapped[list["ExecutorSpecializationOrm"]] = relationship(
        back_populates="executor", cascade="all, delete-orphan"
    )
    tasks: Mapped[list["TaskOrm"]] = relationship(backref="executor")


class TaskResultOrm(Model):
    """Модель таблицы результатов выполнения задач."""
    __tablename__ = "task_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"))
    executor_id: Mapped[int] = mapped_column(ForeignKey("executors.id"))
    task = relationship("TaskOrm", back_populates="results")
    score: Mapped[int]


async def create_tables():
    """Создать все таблицы в базе данных."""
    async with engine.begin() as conn:
        await conn.run_sync(Model.metadata.create_all)


async def delete_tables():
    """Удалить все таблицы из базы данных."""
    async with engine.begin() as conn:
        await conn.run_sync(Model.metadata.drop_all)

class ExecutorSpecializationOrm(Model):
    __tablename__ = "executor_specializations"

    id: Mapped[int] = mapped_column(primary_key=True)
    executor_id: Mapped[int] = mapped_column(ForeignKey("executors.id"))
    specialization: Mapped[str]

    executor: Mapped["ExecutorOrm"] = relationship(back_populates="specializations")
