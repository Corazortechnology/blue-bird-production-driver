"""Configuration loader — reads YAML config once and caches."""

import logging
import os
from typing import Any, Dict

import yaml

_logger = logging.getLogger(__name__)


class ConfigLoader:
    """Singleton config loader for the application."""

    _config: Dict[str, Any] | None = None
    _config_dir = os.path.abspath(os.path.dirname(__file__))

    @classmethod
    def load(cls, path: str | None = None) -> Dict[str, Any]:
        if cls._config is not None:
            return cls._config
        if path is None:
            path = os.path.join(cls._config_dir, "config.yaml")
        _logger.debug("Loading config from %s", path)
        with open(path, "r") as f:
            cls._config = yaml.safe_load(f)
        cls._apply_env_overrides()
        _logger.info("Config loaded (%d top-level keys)", len(cls._config))
        return cls._config

    @classmethod
    def _apply_env_overrides(cls) -> None:
        """Kubernetes / production: set MONGODB_URL and MONGODB_DATABASE as env vars."""
        if cls._config is None:
            return
        if "mongodb" not in cls._config or cls._config["mongodb"] is None:
            cls._config["mongodb"] = {}
        mongo = cls._config["mongodb"]
        if os.environ.get("MONGODB_URL"):
            mongo["url"] = os.environ["MONGODB_URL"]
            _logger.info("mongodb.url overridden from MONGODB_URL environment variable")
        if os.environ.get("MONGODB_DATABASE"):
            mongo["database"] = os.environ["MONGODB_DATABASE"]
            _logger.info("mongodb.database overridden from MONGODB_DATABASE environment variable")

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        cfg = cls.load()
        return cfg.get(key, default)


config = ConfigLoader.load()
