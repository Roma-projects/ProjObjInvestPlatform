"""Для чего нужен этот файл:
Загружает ML-модель и использует её для прогнозов. Сервисный слой связывает API, проверку данных и хранилище.
"""

import logging
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class MLService:
    def __init__(self) -> None:
        self.model: RandomForestRegressor | None = None
        self.version = settings.ml_model_version
        self.load()

    def load(self) -> None:
        path = Path(settings.ml_model_path)
        if path.exists():
            try:
                self.model = joblib.load(path)
                logger.info("Loaded ML model from %s", path)
            except Exception as exc:
                logger.warning("Failed to load model: %s", exc)
                self.model = None
        else:
            logger.info("No ML model at %s, using heuristic", path)

    def predict_rent(
        self, area: float, rooms: int, floor: int | None, price: float | None
    ) -> tuple[float, str]:
        if self.model is not None:
            features = np.array(
                [[area, rooms, floor or 1, price or area * 150_000]],
                dtype=float,
            )
            pred = float(self.model.predict(features)[0])
            return max(pred, 0.0), "ml"
        # Heuristic fallback: ~0.5% of property value / month or area-based
        if price:
            return round(price * 0.005, 2), "heuristic_yield"
        base = area * 800
        room_bonus = rooms * 3000
        floor_factor = 1.0 + (0.01 * ((floor or 1) - 1))
        return round((base + room_bonus) * floor_factor, 2), "heuristic_area"

    def retrain_synthetic(self, n_samples: int = 500) -> int:
        rng = np.random.default_rng(42)
        area = rng.uniform(20, 150, n_samples)
        rooms = rng.integers(1, 5, n_samples)
        floor = rng.integers(1, 20, n_samples)
        price = area * rng.uniform(100_000, 250_000, n_samples)
        rent = area * 700 + rooms * 2500 + floor * 200 + rng.normal(0, 2000, n_samples)
        X = np.column_stack([area, rooms, floor, price])
        model = RandomForestRegressor(n_estimators=50, random_state=42)
        model.fit(X, rent)
        path = Path(settings.ml_model_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, path)
        self.model = model
        logger.info("Retrained model saved to %s (%s samples)", path, n_samples)
        return n_samples


ml_service = MLService()
