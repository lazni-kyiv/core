import datetime
from decimal import Decimal

def json_safe(data):
    """
    Converts anything into JSON-safe format:
    - datetime -> ISO string
    - Decimal -> float
    - nested dict/list supported
    """

    if isinstance(data, dict):
        return {k: json_safe(v) for k, v in data.items()}

    if isinstance(data, list):
        return [json_safe(v) for v in data]

    if isinstance(data, (datetime.datetime, datetime.date)):
        return data.isoformat()

    if isinstance(data, Decimal):
        return float(data)  # or str(data) if you want precision-safe

    return data