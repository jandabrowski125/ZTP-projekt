from datetime import date

from fastapi import HTTPException


def validate_date_range(date_from: date | None, date_to: date | None) -> None:
    today = date.today()

    if date_from is not None and date_from < today:
        raise HTTPException(
            status_code=400,
            detail="date_from cannot be before today",
        )
    if date_to is not None and date_to < today:
        raise HTTPException(
            status_code=400,
            detail="date_to cannot be before today",
        )
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(
            status_code=400,
            detail="date_from must be on or before date_to",
        )
