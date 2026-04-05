const DEFAULT_LOCALE = "es-AR";

export function currency(value: number | null) {
  if (value === null) {
    return "Consultar";
  }

  return new Intl.NumberFormat(DEFAULT_LOCALE, {
    style: "currency",
    currency: "ARS",
    maximumFractionDigits: 0,
  }).format(value);
}

export function dateLabel(iso: string, timeZone?: string | null) {
  return new Intl.DateTimeFormat(DEFAULT_LOCALE, {
    weekday: "short",
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: timeZone ?? undefined,
  }).format(new Date(iso));
}

export function timeOnlyLabel(iso: string, timeZone?: string | null) {
  return new Intl.DateTimeFormat(DEFAULT_LOCALE, {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: timeZone ?? undefined,
  }).format(new Date(iso));
}

export function timeZoneLabel(timeZone?: string | null) {
  if (!timeZone) {
    return "Zona horaria no definida";
  }

  const parts = new Intl.DateTimeFormat(DEFAULT_LOCALE, {
    timeZone,
    timeZoneName: "short",
  }).formatToParts(new Date());

  return parts.find((part) => part.type === "timeZoneName")?.value ?? timeZone;
}

export function timeZoneSummary(timeZone?: string | null) {
  if (!timeZone) {
    return "Zona horaria no definida";
  }

  return `${timeZone} · ${timeZoneLabel(timeZone)}`;
}

export function dateInputDefault() {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60_000;
  return new Date(now.getTime() - offset).toISOString().slice(0, 10);
}

export function localDateBounds(dateValue: string) {
  const start = new Date(`${dateValue}T00:00:00`);
  const end = new Date(start);
  end.setDate(end.getDate() + 1);

  return {
    startIso: start.toISOString(),
    endIso: end.toISOString(),
  };
}
