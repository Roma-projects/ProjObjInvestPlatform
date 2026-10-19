"""Сохраняет информацию о версии AI-модели и её политике в собственной PostgreSQL."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Общая основа SQLAlchemy-модели сервиса Analytic AI."""


class ModelConfig(Base):
    """Аудитирует имя модели и политику, применённую сервисом."""

    __tablename__ = "ai_model_configs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_name: Mapped[str] = mapped_column(String(200), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(50), nullable=False)
    endpoint_host: Mapped[str] = mapped_column(String(255), nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
