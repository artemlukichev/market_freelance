"""Главный модуль запуска FastAPI-приложения."""

from contextlib import asynccontextmanager
from fastapi import FastAPI

from database import create_tables, delete_tables
from router import task_router, user_router, executors_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Создание и удаление таблиц при запуске/остановке приложения."""
    await create_tables()
    print("База готова")
    yield
    await delete_tables()
    print("База очищена")


app = FastAPI(lifespan=lifespan)

# Подключаем роутеры
app.include_router(task_router)
app.include_router(user_router)
app.include_router(executors_router)
