"""Для чего нужен этот файл:
Рассчитывает показатели инвестиционной привлекательности объекта. Сервисный слой связывает API, проверку данных и хранилище.
"""

"""Investment scoring for listings."""


def compute_investment_score(
    *,
    price: float,
    area: float,
    rooms: int,
    rent_estimate: float,
) -> tuple[float, float, str, str]:
    if price <= 0:
        return 0.0, 0.0, "high", "Invalid price"

    annual_rent = rent_estimate * 12
    annual_yield = (annual_rent / price) * 100

    # Score 0-100 based on yield and price/m2 sanity
    price_per_m2 = price / max(area, 1)
    yield_score = min(max(annual_yield * 10, 0), 60)  # ~6% yield => 60
    liquidity = 20 if rooms in (1, 2, 3) else 10
    sanity = 20 if 50_000 <= price_per_m2 <= 500_000 else 8
    score = round(min(yield_score + liquidity + sanity, 100), 2)

    if annual_yield >= 7:
        risk = "low"
    elif annual_yield >= 4:
        risk = "medium"
    else:
        risk = "high"

    commentary = (
        f"Ориентировочная годовая доходность ~{annual_yield:.2f}%. "
        f"Цена за м² ≈ {price_per_m2:,.0f}."
    )
    return score, round(annual_yield, 2), risk, commentary
