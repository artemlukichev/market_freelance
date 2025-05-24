"""Маршруты FastAPI приложения: задачи, пользователи, исполнители."""

import datetime

from jose import JWTError, jwt
from sqlalchemy import select
from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordBearer

from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from database import ExecutorOrm, new_session
from repository import TaskRepository, UserRepository, ExecutorRepository
from schemas import (
    STask,
    STaskAdd,
    STaskId,
    STaskClose,
    ExecutorWithTasksAndScore,
    STaskNameUpdate,
    UserRegister,
    UserLogin,
    Token,
    ExecutorCreate,
    AddSpecialization
)

# ---------------------- Task Router ----------------------

task_router = APIRouter(
    prefix="/tasks",
    tags=["Задания"]
)


@task_router.post("")
async def add_task(task: STaskAdd) -> STaskId:
    """Добавить новую задачу."""
    new_task_id = await TaskRepository.add_task(task)
    return {"id": new_task_id}


@task_router.get("")
async def get_tasks() -> list[STask]:
    """Получить список всех задач."""
    tasks = await TaskRepository.get_tasks()
    return tasks


@task_router.put("/{task_id}/name")
async def update_task_name(task_id: int, task_name_update: STaskNameUpdate):
    """Обновить имя задачи."""
    updated = await TaskRepository.update_task_name(task_id, task_name_update.name)
    if not updated:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return {"message": "Имя задачи обновлено"}


@task_router.post("/{task_id}/close")
async def close_task(task_id: int, task_close_data: STaskClose):
    """Закрыть задачу и выставить оценку."""
    try:
        await TaskRepository.close_task(task_id, task_close_data.executor_id, task_close_data.score)
        return {"message": "Задача закрыта и оценка выставлена"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@task_router.put("/{task_id}/assign")
async def assign_task(task_id: int, executor_id: int):
    """Назначить исполнителя задаче."""
    assigned = await TaskRepository.assign_executor(task_id, executor_id)
    if not assigned:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return {"message": "Исполнитель назначен"}


@task_router.post("/{task_id}/assign-greedy")
async def assign_best_executor_greedy(task_id: int):
    """Назначить лучшего исполнителя на задачу (жадный алгоритм)."""
    try:
        result = await TaskRepository.assign_task_to_best_executor_greedy(task_id)
        return {"message": "Исполнитель назначен", **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

# ---------------------- User Router ----------------------

user_router = APIRouter(
    prefix="/users",
    tags=["Пользователи"],
)


@user_router.post("/register")
async def register(user: UserRegister):
    """Регистрация нового пользователя."""
    existing_user = await UserRepository.get_user(user.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Пользователь уже существует")

    user_id = await UserRepository.create_user(user.username, user.password)
    return {"id": user_id}


@user_router.post("/login", response_model=Token)
async def login(user: UserLogin):
    """Авторизация пользователя и выдача JWT."""
    db_user = await UserRepository.get_user(user.username)

    if not db_user or not UserRepository.verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Неверные учетные данные")

    access_token_expires = datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)

    return {"access_token": access_token, "token_type": "bearer"}


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


@user_router.get("/protected")
async def protected_route(token: str = Depends(oauth2_scheme)):
    """Пример защищенного маршрута."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError as e:
        raise credentials_exception from e

    return {"message": "Это защищенный маршрут", "user": username}


@user_router.delete("/delete")
async def delete_user(token: str = Depends(oauth2_scheme)):
    """Удаление текущего пользователя по токену."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError as e:
        raise credentials_exception from e

    deleted = await UserRepository.delete_user(username)
    if not deleted:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    return {"message": "Пользователь удален"}


@user_router.get("")
async def get_users():
    """Получить список всех пользователей и исполнителей."""
    users = await UserRepository.get_all_users()

    async with new_session() as session:
        executors_result = await session.execute(select(ExecutorOrm))
        executors = executors_result.scalars().all()

    combined = [
        {"id": user.id, "username": user.username, "role": "user"}
        for user in users
    ] + [
        {"id": executor.id, "username": executor.username, "role": "executor"}
        for executor in executors
    ]

    return combined

# ---------------------- Executors Router ----------------------

executors_router = APIRouter(
    prefix="/executors",
    tags=["Исполнители"]
)


@executors_router.post("")
async def create_executor(executor: ExecutorCreate):
    """Создать нового исполнителя."""
    executor_id = await ExecutorRepository.create_executor(executor.username, executor.specializations)
    return {"id": executor_id}


@executors_router.get("/with-tasks", response_model=list[ExecutorWithTasksAndScore])
async def get_executors_with_tasks_and_avg_score():
    """Получить исполнителей с их задачами и средней оценкой."""
    data = await ExecutorRepository.get_executors_with_tasks_and_avg_score()
    return data

@executors_router.post("/{executor_id}/specializations")
async def add_specialization(executor_id: int, data: AddSpecialization):
    await ExecutorRepository.add_specialization(executor_id, data.specialization)
    return {"message": "Specialization added"}

# ---------------------- Utility ----------------------

def create_access_token(data: dict, expires_delta: datetime.timedelta | None = None):
    """Создание JWT-токена с истечением срока действия."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.datetime.utcnow() + expires_delta
    else:
        expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=15)

    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

