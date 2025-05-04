from sqlalchemy import select, update, func
from passlib.context import CryptContext

from database import TaskOrm, new_session, UserOrm, ExecutorOrm, TaskResultOrm
from schemas import STask, STaskAdd


class TaskRepository:
    """Репозиторий для работы с задачами."""

    @classmethod
    async def add_task(cls, task: STaskAdd) -> int:
        """Добавить задачу в БД и вернуть её ID."""
        async with new_session() as session:
            data = task.model_dump()
            new_task = TaskOrm(**data)
            session.add(new_task)
            await session.flush()
            await session.commit()
            return new_task.id

    @classmethod
    async def get_tasks(cls) -> list[STask]:
        """Получить все задачи."""
        async with new_session() as session:
            result = await session.execute(select(TaskOrm))
            task_models = result.scalars().all()
            return [STask.model_validate(task) for task in task_models]

    @classmethod
    async def update_task_name(cls, task_id: int, new_name: str) -> bool:
        """Обновить имя задачи."""
        async with new_session() as session:
            query = update(TaskOrm).where(TaskOrm.id == task_id).values(name=new_name)
            result = await session.execute(query)
            await session.commit()
            return result.rowcount > 0

    @classmethod
    async def close_task(cls, task_id: int, executor_id: int, score: int) -> bool:
        """Закрыть задачу с оценкой исполнителя."""
        if not 0 <= score <= 10:
            raise ValueError("Оценка должна быть от 0 до 10")

        async with new_session() as session:
            task_result = TaskResultOrm(task_id=task_id, executor_id=executor_id, score=score)
            session.add(task_result)
            await session.commit()
            return True

    @classmethod
    async def assign_executor(cls, task_id: int, executor_id: int) -> bool:
        """Назначить исполнителя на задачу."""
        async with new_session() as session:
            query = update(TaskOrm).where(TaskOrm.id == task_id).values(executor_id=executor_id)
            result = await session.execute(query)
            await session.commit()
            return result.rowcount > 0

    @classmethod
    async def assign_task_to_best_executor_greedy(cls, task_id: int) -> dict:
        """Жадный выбор лучшего исполнителя для задачи."""
        async with new_session() as session:
            stats_query = (
                select(
                    ExecutorOrm.id,
                    ExecutorOrm.username,
                    func.count(TaskOrm.id).label("task_count"),
                    func.avg(TaskResultOrm.score).label("avg_score")
                )
                .outerjoin(TaskOrm, TaskOrm.executor_id == ExecutorOrm.id)
                .outerjoin(TaskResultOrm, TaskResultOrm.executor_id == ExecutorOrm.id)
                .group_by(ExecutorOrm.id)
            )
            result = await session.execute(stats_query)
            stats = result.all()

            if not stats:
                raise ValueError("Нет доступных исполнителей")

            best = min(
                stats,
                key=lambda x: (x.task_count, -(x.avg_score or 0))
            )

            executor_id, username, _, _ = best

            update_query = update(TaskOrm).where(TaskOrm.id == task_id).values(executor_id=executor_id)
            result = await session.execute(update_query)
            await session.commit()

            if result.rowcount == 0:
                raise ValueError("Задача не найдена")

            return {
                "executor_id": executor_id,
                "executor_username": username
            }


class UserRepository:
    """Репозиторий для управления пользователями."""

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    @classmethod
    async def create_user(cls, username: str, password: str) -> int:
        """Создать нового пользователя с хэшированным паролем."""
        hashed_password = cls.pwd_context.hash(password)
        async with new_session() as session:
            new_user = UserOrm(username=username, hashed_password=hashed_password)
            session.add(new_user)
            await session.flush()
            await session.commit()
            return new_user.id

    @classmethod
    async def get_user(cls, username: str) -> UserOrm | None:
        """Получить пользователя по имени."""
        async with new_session() as session:
            result = await session.execute(select(UserOrm).where(UserOrm.username == username))
            return result.scalars().first()

    @classmethod
    def verify_password(cls, plain_password: str, hashed_password: str) -> bool:
        """Проверить пароль."""
        return cls.pwd_context.verify(plain_password, hashed_password)

    @classmethod
    async def get_all_users(cls) -> list[UserOrm]:
        """Получить список всех пользователей."""
        async with new_session() as session:
            result = await session.execute(select(UserOrm))
            return result.scalars().all()

    @classmethod
    async def delete_user(cls, username: str) -> bool:
        """Удалить пользователя по имени."""
        async with new_session() as session:
            result = await session.execute(select(UserOrm).where(UserOrm.username == username))
            user = result.scalars().first()

            if not user:
                return False

            await session.delete(user)
            await session.commit()
            return True


class ExecutorRepository:
    """Репозиторий для управления исполнителями."""

    @classmethod
    async def create_executor(cls, username: str) -> int:
        """Создать нового исполнителя."""
        async with new_session() as session:
            executor = ExecutorOrm(username=username)
            session.add(executor)
            await session.flush()
            await session.commit()
            return executor.id

    @classmethod
    async def get_executors_with_tasks_and_avg_score(cls):
        """Получить всех исполнителей с задачами и средней оценкой."""
        async with new_session() as session:
            executor_query = (
                select(ExecutorOrm)
                .join(TaskOrm, ExecutorOrm.id == TaskOrm.executor_id)
                .distinct()
            )
            executor_result = await session.execute(executor_query)
            executors = executor_result.scalars().all()

            data = []

            for executor in executors:
                tasks_query = select(TaskOrm).where(TaskOrm.executor_id == executor.id)
                tasks_result = await session.execute(tasks_query)
                tasks = tasks_result.scalars().all()

                score_query = select(func.avg(TaskResultOrm.score)).where(TaskResultOrm.executor_id == executor.id)
                score_result = await session.execute(score_query)
                avg_score = score_result.scalar()

                data.append({
                    "executor_id": executor.id,
                    "executor_username": executor.username,
                    "tasks": [
                        {"id": task.id, "name": task.name, "description": task.description}
                        for task in tasks
                    ],
                    "average_score": round(avg_score, 2) if avg_score is not None else None
                })

            return data
