"""Pydantic-схемы для валидации входных и выходных данных API."""

from pydantic import BaseModel, ConfigDict


class STaskAdd(BaseModel):
    name: str
    description: str | None = None
    author_id: int
    subject_area: str


class STask(STaskAdd):
    """Схема задачи с ID и исполнителем."""
    id: int
    executor_id: int | None
    model_config = ConfigDict(from_attributes=True)


class STaskId(BaseModel):
    """Схема, содержащая только ID задачи."""
    id: int


class Executor(BaseModel):
    """Схема исполнителя."""
    id: int
    username: str


class STaskExecutorUpdate(BaseModel):
    """Схема для обновления исполнителя задачи."""
    executor_id: int


class STaskNameUpdate(BaseModel):
    """Схема для обновления имени задачи."""
    name: str


class STaskClose(BaseModel):
    """Схема для закрытия задачи и выставления оценки."""
    executor_id: int
    score: int


class UserRegister(BaseModel):
    """Схема регистрации пользователя."""
    username: str
    password: str


class UserLogin(BaseModel):
    """Схема авторизации пользователя."""
    username: str
    password: str


class Token(BaseModel):
    """Схема ответа с JWT-токеном."""
    access_token: str
    token_type: str = "bearer"


class TaskShort(BaseModel):
    """Краткая информация о задаче."""
    id: int
    name: str
    description: str | None


class ExecutorWithTasksAndScore(BaseModel):
    """Исполнитель с задачами и средней оценкой."""
    executor_id: int
    executor_username: str
    specialization: str | None = None
    tasks: list[TaskShort]
    average_score: float | None
    average_execution_time_hours: float | None = None


class ExecutorCreate(BaseModel):
    username: str
    specializations: list[str] = []


class AddSpecialization(BaseModel):
    specialization: str