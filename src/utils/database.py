"""
数据库工具模块
"""
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import settings


class Database:
    """数据库连接管理类"""

    _engine: Optional[Engine] = None
    _session_factory: Optional[sessionmaker] = None

    @classmethod
    def get_engine(cls) -> Engine:
        """获取数据库引擎"""
        if cls._engine is None:
            cls._engine = create_engine(
                settings.DATABASE_URL,
                pool_size=settings.DATABASE_POOL_SIZE,
                max_overflow=20,
                pool_pre_ping=True,
                echo=settings.DEBUG,
            )
        return cls._engine

    @classmethod
    def get_session_factory(cls) -> sessionmaker:
        """获取会话工厂"""
        if cls._session_factory is None:
            cls._session_factory = sessionmaker(
                bind=cls.get_engine(),
                autocommit=False,
                autoflush=False,
            )
        return cls._session_factory

    @classmethod
    @contextmanager
    def get_session(cls) -> Generator[Session, None, None]:
        """获取数据库会话的上下文管理器"""
        session = cls.get_session_factory()()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @classmethod
    def dispose(cls) -> None:
        """释放数据库连接"""
        if cls._engine is not None:
            cls._engine.dispose()
            cls._engine = None
            cls._session_factory = None


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """获取数据库会话的便捷函数"""
    with Database.get_session() as session:
        yield session


def execute_sql(sql: str, params: Optional[dict] = None) -> None:
    """执行SQL语句"""
    with Database.get_session() as session:
        session.execute(text(sql), params or {})
