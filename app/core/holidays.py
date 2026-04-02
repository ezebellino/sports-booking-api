from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import requests

NAGER_PUBLIC_HOLIDAYS_URL = "https://date.nager.at/api/v3/PublicHolidays/{year}/{country_code}"


class HolidayProviderError(RuntimeError):
    pass


@dataclass(slots=True)
class HolidayRecord:
    date: str
    local_name: str
    name: str
    country_code: str
    global_holiday: bool
    counties: list[str] | None
    launch_year: int | None
    types: list[str]


def fetch_public_holidays(year: int, country_code: str) -> list[HolidayRecord]:
    normalized_country_code = country_code.strip().upper()
    if len(normalized_country_code) != 2:
        raise HolidayProviderError("El código de país debe tener 2 letras, por ejemplo AR.")

    try:
        response = requests.get(
            NAGER_PUBLIC_HOLIDAYS_URL.format(year=year, country_code=normalized_country_code),
            timeout=10,
        )
    except requests.RequestException as exc:
        raise HolidayProviderError("No pudimos consultar el calendario de feriados.") from exc

    if response.status_code != 200:
        raise HolidayProviderError("El proveedor de feriados devolvió una respuesta inválida.")

    payload = response.json()
    holidays: list[HolidayRecord] = []
    for item in payload:
        holidays.append(
            HolidayRecord(
                date=item["date"],
                local_name=item.get("localName") or item.get("name") or "Feriado",
                name=item.get("name") or item.get("localName") or "Holiday",
                country_code=item.get("countryCode") or normalized_country_code,
                global_holiday=bool(item.get("global")),
                counties=item.get("counties"),
                launch_year=item.get("launchYear"),
                types=item.get("types") or [],
            )
        )
    return holidays


def filter_holidays_by_month(holidays: list[HolidayRecord], month: int | None) -> list[HolidayRecord]:
    if month is None:
        return holidays
    return [holiday for holiday in holidays if date.fromisoformat(holiday.date).month == month]
