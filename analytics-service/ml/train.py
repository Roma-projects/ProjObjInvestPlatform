"""Для чего нужен этот файл:
Подготавливает данные и обучает ML-модель. Сохранённая модель используется сервисом аналитики для прогнозов.
"""

"""
Train rent estimation model on synthetic data.

Usage (from analytics-service directory):
    python ml/train.py
"""

from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "ml" / "models" / "rent_model.joblib"


def main() -> None:
    rng = np.random.default_rng(42)
    n = 800
    area = rng.uniform(20, 150, n)
    rooms = rng.integers(1, 5, n)
    floor = rng.integers(1, 20, n)
    price = area * rng.uniform(100_000, 250_000, n)
    rent = area * 700 + rooms * 2500 + floor * 200 + rng.normal(0, 2000, n)
    X = np.column_stack([area, rooms, floor, price])
    model = RandomForestRegressor(n_estimators=80, random_state=42)
    model.fit(X, rent)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, OUT)
    print(f"Saved model to {OUT}")


if __name__ == "__main__":
    main()
