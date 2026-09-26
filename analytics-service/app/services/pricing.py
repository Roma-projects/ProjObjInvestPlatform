"""Для чего нужен этот файл:
Рассчитывает ориентировочную стоимость или аренду объекта. Сервисный слой связывает API, проверку данных и хранилище.
"""

"""Regional rent pricing heuristics."""

from decimal import Decimal

REGION_MULTIPLIERS = {
    "moscow": 1.8,
    "spb": 1.4,
    "default": 1.0,
    "ekaterinburg": 1.1,
    "novosibirsk": 1.05,
}


def estimate_rent(
    *,
    area: float,
    rooms: int,
    floor: int | None,
    region: str,
    ml_estimate: float,
) -> Decimal:
    mult = REGION_MULTIPLIERS.get(region.lower(), REGION_MULTIPLIERS["default"])
    adjusted = ml_estimate * mult
    # Soft clamp by area sanity
    min_rent = area * 400 * mult
    max_rent = area * 2500 * mult
    value = min(max(adjusted, min_rent), max_rent)
    if floor and floor > 15:
        value *= 0.98
    if rooms >= 4:
        value *= 1.05
    return Decimal(str(round(value, 2)))
