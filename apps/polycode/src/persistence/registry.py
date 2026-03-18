"""SQLAlchemy model registry with auto-registration via __init_subclass__."""

import logging
from typing import Type

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

log = logging.getLogger(__name__)


METADATA = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)


class ModelRegistry:
    """Central registry for ORM models from all modules."""

    _models: dict[str, Type[DeclarativeBase]] = {}
    _modules: set[str] = set()

    @classmethod
    def register_model(cls, model: Type[DeclarativeBase], module_name: str) -> None:
        """Register a single model under its module name."""
        key = f"{module_name}.{model.__tablename__}"
        cls._models[key] = model

    @classmethod
    def register_module(cls, module_name: str) -> None:
        """Mark a module as having been processed."""
        cls._modules.add(module_name)

    @classmethod
    def is_registered(cls, module_name: str) -> bool:
        return module_name in cls._modules

    @classmethod
    def create_all(cls, engine) -> None:
        """Create all registered tables in one pass."""
        METADATA.create_all(bind=engine)
        log.info(f"📊 Created {len(cls._models)} tables from {len(cls._modules)} modules")

    @classmethod
    def get_models_for_module(cls, module_name: str) -> list[Type[DeclarativeBase]]:
        """Return all models belonging to a module."""
        prefix = f"{module_name}."
        return [m for key, m in cls._models.items() if key.startswith(prefix)]

    @classmethod
    def all_models(cls) -> dict[str, Type[DeclarativeBase]]:
        """Return all registered models as {module.table: model}."""
        return dict(cls._models)

    @classmethod
    def reset(cls) -> None:
        """Clear registry (for testing)."""
        cls._models.clear()
        cls._modules.clear()


class RegisteredBase(DeclarativeBase):
    """Base class for ORM models with auto-registration.

    All models across all modules inherit from this. Each model must
    declare __module_name__ to identify its owning module.

    Usage:

        class MyModel(RegisteredBase):
            __module_name__ = "my_module"
            __tablename__ = "my_table"

            id: Mapped[int] = mapped_column(primary_key=True)

    The __init_subclass__ hook automatically registers the model with
    ModelRegistry when the class is defined (at import time).

    If __module_name__ is omitted, the registry attempts to infer it from
    the class's __module__ attribute (e.g., 'src.retro.persistence' -> 'retro').
    """

    metadata = METADATA
    __module_name__: str

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)

        if getattr(cls, "__abstract__", False):
            return

        module_name = getattr(cls, "__module_name__", None)
        if not module_name:
            parts = cls.__module__.split(".")
            if len(parts) >= 2 and parts[0] == "src":
                module_name = parts[1]

        if module_name:
            ModelRegistry.register_model(cls, module_name)
            ModelRegistry.register_module(module_name)
            log.debug(f"📊 Auto-registered: {module_name}.{cls.__tablename__}")
        else:
            log.warning(
                f"⚠️ {cls.__name__} has no __module_name__ and cannot be inferred from __module__={cls.__module__!r}"
            )
