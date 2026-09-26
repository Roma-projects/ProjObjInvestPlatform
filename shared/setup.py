"""Для чего нужен этот файл:
Описывает пакет shared: имя, версию, минимальную версию Python и необходимые библиотеки.
"""

from setuptools import find_packages, setup

setup(
    name="shared",
    version="0.1.0",
    description="Shared utilities for Real Estate Aggregator microservices",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "pydantic>=2.0",
        "pydantic-settings>=2.0",
        "sqlalchemy[asyncio]>=2.0",
        "asyncpg>=0.29",
        "redis>=5.0",
        "aio-pika>=9.0",
        "passlib[bcrypt]>=1.7",
        "python-jose[cryptography]>=3.3",
        "email-validator>=2.0",
    ],
)
