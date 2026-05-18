from app.config import settings


def compute_fare(distance_km: float, duration_min: float) -> float:
    fare = settings.BASE_FARE_KES + distance_km * settings.PER_KM_KES + duration_min * settings.PER_MIN_KES
    # Round to nearest 10 KES
    return float(round(fare / 10.0) * 10)
