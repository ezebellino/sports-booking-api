import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CalendarClock,
  CircleAlert,
  LoaderCircle,
  PencilLine,
  Plus,
  Save,
  Shield,
  TimerReset,
} from "lucide-react";
import { useMemo, useState } from "react";
import { AdminNav } from "../components/admin-nav";
import { AppHeader } from "../components/app-header";
import { EmptyState } from "../components/empty-state";
import { LoadingCard } from "../components/loading-card";
import { SectionTitle } from "../components/section-title";
import { api, type TimeSlot } from "../lib/api";
import { dateInputDefault, dateLabel, localDateBounds } from "../lib/format";

function toLocalDateTimeInput(iso: string) {
  const date = new Date(iso);
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

function combineDateTime(date: string, time: string) {
  return new Date(`${date}T${time}`).toISOString();
}

type PreviewCourtStatus = {
  courtId: string;
  courtName: string;
  exists: boolean;
};

type PreviewRow = {
  startsAt: string;
  endsAt: string;
  createCount: number;
  skippedCount: number;
  courtStatuses: PreviewCourtStatus[];
};

export function AdminTimeslotsPage() {
  const queryClient = useQueryClient();
  const [selectedDate, setSelectedDate] = useState(dateInputDefault);
  const [filterCourtId, setFilterCourtId] = useState<string>("");
  const [bulkCourtIds, setBulkCourtIds] = useState<string[]>([]);
  const [windowStart, setWindowStart] = useState("09:00");
  const [windowEnd, setWindowEnd] = useState("23:00");
  const [slotMinutes, setSlotMinutes] = useState("60");
  const [capacity, setCapacity] = useState("1");
  const [price, setPrice] = useState("");
  const [isActive, setIsActive] = useState(true);
  const [bulkError, setBulkError] = useState<string | null>(null);
  const [bulkSuccess, setBulkSuccess] = useState<string | null>(null);
  const [editingTimeSlotId, setEditingTimeSlotId] = useState<string | null>(null);
  const [editStartsAt, setEditStartsAt] = useState("");
  const [editEndsAt, setEditEndsAt] = useState("");
  const [editCapacity, setEditCapacity] = useState("1");
  const [editPrice, setEditPrice] = useState("");
  const [editIsActive, setEditIsActive] = useState(true);
  const [editError, setEditError] = useState<string | null>(null);
  const [editSuccess, setEditSuccess] = useState<string | null>(null);
  const dayBounds = useMemo(() => localDateBounds(selectedDate), [selectedDate]);

  const courtsQuery = useQuery({
    queryKey: ["courts", "all-admin"],
    queryFn: () => api.listCourts({}),
  });

  const timeslotsQuery = useQuery({
    queryKey: ["admin-timeslots", filterCourtId, selectedDate],
    queryFn: () =>
      api.listTimeslots({
        courtId: filterCourtId || undefined,
        dateFrom: dayBounds.startIso,
        dateTo: dayBounds.endIso,
      }),
  });

  const existingDayTimeslotsQuery = useQuery({
    queryKey: ["admin-timeslots-preview", selectedDate],
    queryFn: () =>
      api.listTimeslots({
        dateFrom: dayBounds.startIso,
        dateTo: dayBounds.endIso,
      }),
  });

  const courtsById = useMemo(
    () => new Map((courtsQuery.data ?? []).map((court) => [court.id, court])),
    [courtsQuery.data],
  );

  const previewSlots = useMemo(() => {
    const parsedSlotMinutes = Number(slotMinutes);

    if (!selectedDate || !windowStart || !windowEnd || !Number.isFinite(parsedSlotMinutes) || parsedSlotMinutes <= 0) {
      return [] as Array<{ startsAt: string; endsAt: string }>;
    }

    const slots: Array<{ startsAt: string; endsAt: string }> = [];
    const start = new Date(`${selectedDate}T${windowStart}`);
    const endLimit = new Date(`${selectedDate}T${windowEnd}`);

    if (Number.isNaN(start.getTime()) || Number.isNaN(endLimit.getTime()) || start >= endLimit) {
      return slots;
    }

    let currentStart = new Date(start);
    while (currentStart < endLimit) {
      const currentEnd = new Date(currentStart.getTime() + parsedSlotMinutes * 60_000);
      slots.push({
        startsAt: currentStart.toISOString(),
        endsAt: currentEnd.toISOString(),
      });
      currentStart = currentEnd;
    }

    return slots;
  }, [selectedDate, slotMinutes, windowEnd, windowStart]);

  const previewSummary = useMemo(() => {
    const selectedCourtSet = new Set(bulkCourtIds);
    const existingKeys = new Set(
      (existingDayTimeslotsQuery.data ?? [])
        .filter((timeslot) => selectedCourtSet.has(timeslot.court_id))
        .map((timeslot) => `${timeslot.court_id}|${timeslot.starts_at}|${timeslot.ends_at}`),
    );

    const rows: PreviewRow[] = previewSlots.map((slot) => {
      const courtStatuses = bulkCourtIds.map((courtId) => {
        const key = `${courtId}|${slot.startsAt}|${slot.endsAt}`;
        const courtName = courtsById.get(courtId)?.name ?? "Cancha";
        return {
          courtId,
          courtName,
          exists: existingKeys.has(key),
        };
      });

      const skippedCount = courtStatuses.filter((courtStatus) => courtStatus.exists).length;
      const createCount = courtStatuses.length - skippedCount;

      return {
        ...slot,
        createCount,
        skippedCount,
        courtStatuses,
      };
    });

    const totalCreateCount = rows.reduce((sum, row) => sum + row.createCount, 0);
    const totalSkippedCount = rows.reduce((sum, row) => sum + row.skippedCount, 0);
    const crossesMidnight = rows.some(
      (row) => new Date(row.endsAt).toISOString().slice(0, 10) !== selectedDate,
    );

    return {
      rows,
      totalCreateCount,
      totalSkippedCount,
      crossesMidnight,
    };
  }, [bulkCourtIds, courtsById, existingDayTimeslotsQuery.data, previewSlots, selectedDate]);

  const bulkCreateMutation = useMutation({
    mutationFn: api.bulkCreateTimeslots,
    onSuccess: (result) => {
      setBulkError(null);
      setEditSuccess(null);
      setBulkSuccess(
        `Se crearon ${result.created_count} turnos y se omitieron ${result.skipped_count}.`,
      );
      void queryClient.invalidateQueries({ queryKey: ["admin-timeslots"] });
      void queryClient.invalidateQueries({ queryKey: ["admin-timeslots-preview"] });
      void queryClient.invalidateQueries({ queryKey: ["timeslots"] });
    },
    onError: (error) => {
      setBulkSuccess(null);
      setBulkError(error instanceof Error ? error.message : "No pudimos crear los turnos.");
    },
  });

  const updateTimeSlotMutation = useMutation({
    mutationFn: ({ timeslotId, payload }: { timeslotId: string; payload: Parameters<typeof api.updateTimeslot>[1] }) =>
      api.updateTimeslot(timeslotId, payload),
    onSuccess: () => {
      setEditError(null);
      setBulkSuccess(null);
      setEditSuccess("Turno actualizado correctamente.");
      void queryClient.invalidateQueries({ queryKey: ["admin-timeslots"] });
      void queryClient.invalidateQueries({ queryKey: ["admin-timeslots-preview"] });
      void queryClient.invalidateQueries({ queryKey: ["timeslots"] });
      setEditingTimeSlotId(null);
    },
    onError: (error) => {
      setEditSuccess(null);
      setEditError(error instanceof Error ? error.message : "No pudimos actualizar el turno.");
    },
  });

  function toggleCourt(courtId: string) {
    setBulkCourtIds((current) =>
      current.includes(courtId) ? current.filter((id) => id !== courtId) : [...current, courtId],
    );
  }

  function handleBulkSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBulkError(null);
    setBulkSuccess(null);

    if (!bulkCourtIds.length) {
      setBulkError("Seleccioná al menos una cancha.");
      return;
    }

    const parsedSlotMinutes = Number(slotMinutes);
    const parsedCapacity = Number(capacity);

    if (!Number.isFinite(parsedSlotMinutes) || parsedSlotMinutes <= 0) {
      setBulkError("La duración del turno debe ser mayor a 0 minutos.");
      return;
    }

    if (!Number.isFinite(parsedCapacity) || parsedCapacity < 1) {
      setBulkError("La capacidad debe ser un número mayor o igual a 1.");
      return;
    }

    bulkCreateMutation.mutate({
      court_ids: bulkCourtIds,
      window_starts_at: combineDateTime(selectedDate, windowStart),
      window_ends_at: combineDateTime(selectedDate, windowEnd),
      slot_minutes: parsedSlotMinutes,
      capacity: parsedCapacity,
      price: price ? Number(price) : null,
      is_active: isActive,
    });
  }

  function beginEdit(timeslot: TimeSlot) {
    setEditingTimeSlotId(timeslot.id);
    setEditStartsAt(toLocalDateTimeInput(timeslot.starts_at));
    setEditEndsAt(toLocalDateTimeInput(timeslot.ends_at));
    setEditCapacity(String(timeslot.capacity));
    setEditPrice(timeslot.price !== null ? String(timeslot.price) : "");
    setEditIsActive(timeslot.is_active);
    setEditError(null);
    setEditSuccess(null);
  }

  function handleEditSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!editingTimeSlotId) {
      return;
    }

    const parsedCapacity = Number(editCapacity);
    if (!Number.isFinite(parsedCapacity) || parsedCapacity < 1) {
      setEditError("La capacidad debe ser un número mayor o igual a 1.");
      return;
    }

    updateTimeSlotMutation.mutate({
      timeslotId: editingTimeSlotId,
      payload: {
        starts_at: new Date(editStartsAt).toISOString(),
        ends_at: new Date(editEndsAt).toISOString(),
        capacity: parsedCapacity,
        price: editPrice ? Number(editPrice) : null,
        is_active: editIsActive,
      },
    });
  }

  return (
    <>
      <AppHeader />
      <section className="space-y-6">
        <AdminNav />

        <SectionTitle
          eyebrow="Admin"
          title="Gestión automática de turnos"
          description="Generá bloques completos por rango horario, elegí la duración de cada turno y repetí la carga en varias canchas. También podés editar turnos ya creados desde la misma pantalla."
        />

        <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
          <form className="shell-card space-y-4 p-5" onSubmit={handleBulkSubmit}>
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-amber-100 text-amber-700">
                <Shield size={18} />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-950">Generación masiva</h3>
                <p className="text-sm text-slate-500">Ideal para cargar una jornada completa de una o varias canchas.</p>
              </div>
            </div>

            <div>
              <label className="mb-2 block text-sm font-semibold text-slate-700" htmlFor="bulk-date">
                Día
              </label>
              <input
                id="bulk-date"
                className="field"
                type="date"
                value={selectedDate}
                onChange={(event) => setSelectedDate(event.target.value)}
              />
            </div>

            <div>
              <p className="mb-2 block text-sm font-semibold text-slate-700">Canchas</p>
              <div className="grid gap-2 sm:grid-cols-2">
                {courtsQuery.data?.map((court) => (
                  <label
                    key={court.id}
                    className={`rounded-2xl border px-4 py-3 text-sm transition ${
                      bulkCourtIds.includes(court.id)
                        ? "border-slate-900 bg-slate-900 text-white"
                        : "border-slate-200 bg-white text-slate-700"
                    }`}
                  >
                    <input
                      className="mr-2"
                      type="checkbox"
                      checked={bulkCourtIds.includes(court.id)}
                      onChange={() => toggleCourt(court.id)}
                    />
                    {court.name}
                  </label>
                ))}
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-700" htmlFor="window-start">
                  Desde
                </label>
                <input id="window-start" className="field" type="time" value={windowStart} onChange={(event) => setWindowStart(event.target.value)} />
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-700" htmlFor="window-end">
                  Hasta
                </label>
                <input id="window-end" className="field" type="time" value={windowEnd} onChange={(event) => setWindowEnd(event.target.value)} />
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-700" htmlFor="slot-minutes">
                  Duración
                </label>
                <select id="slot-minutes" className="field" value={slotMinutes} onChange={(event) => setSlotMinutes(event.target.value)}>
                  <option value="60">60 min</option>
                  <option value="90">90 min</option>
                  <option value="120">120 min</option>
                </select>
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-700" htmlFor="bulk-capacity">
                  Capacidad
                </label>
                <input id="bulk-capacity" className="field" type="number" min="1" value={capacity} onChange={(event) => setCapacity(event.target.value)} />
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-700" htmlFor="bulk-price">
                  Precio
                </label>
                <input id="bulk-price" className="field" type="number" min="0" step="1" value={price} onChange={(event) => setPrice(event.target.value)} placeholder="Opcional" />
              </div>
            </div>

            <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
              <input type="checkbox" checked={isActive} onChange={(event) => setIsActive(event.target.checked)} />
              Crear los turnos como activos
            </label>

            <div className="rounded-3xl border border-slate-200 bg-slate-50 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-slate-900">Vista previa del bloque</p>
                  <p className="text-sm text-slate-500">
                    {previewSlots.length
                      ? `Se crearían ${previewSummary.totalCreateCount} turnos y se omitirían ${previewSummary.totalSkippedCount}.`
                      : "Completá el rango y la duración para ver los turnos que se van a crear."}
                  </p>
                </div>
                {previewSlots.length ? (
                  <span className="rounded-full bg-slate-900 px-3 py-1 text-xs font-semibold text-white">
                    {slotMinutes} min
                  </span>
                ) : null}
              </div>

              {previewSlots.length ? (
                <>
                  {existingDayTimeslotsQuery.isLoading ? (
                    <div className="mt-3">
                      <LoadingCard label="Verificando conflictos del día..." />
                    </div>
                  ) : (
                    <div className="mt-3 space-y-2">
                      {previewSummary.rows.map((slot) => (
                        <div
                          key={slot.startsAt}
                          className="rounded-2xl border border-slate-200 bg-white px-3 py-3 text-sm"
                        >
                          <div className="flex flex-wrap items-center justify-between gap-3">
                            <div className="font-semibold text-slate-800">
                              {dateLabel(slot.startsAt).split(", ").pop()} - {dateLabel(slot.endsAt).split(", ").pop()}
                            </div>
                            <div className="flex flex-wrap gap-2 text-xs font-semibold">
                              {slot.createCount ? (
                                <span className="rounded-full bg-emerald-50 px-3 py-1 text-emerald-700">
                                  Crear {slot.createCount}
                                </span>
                              ) : null}
                              {slot.skippedCount ? (
                                <span className="rounded-full bg-amber-50 px-3 py-1 text-amber-700">
                                  Omitir {slot.skippedCount}
                                </span>
                              ) : null}
                            </div>
                          </div>

                          <div className="mt-3 flex flex-wrap gap-2">
                            {slot.courtStatuses.map((courtStatus) => (
                              <span
                                key={`${slot.startsAt}-${courtStatus.courtId}`}
                                className={`rounded-full px-3 py-1 text-xs font-semibold ${
                                  courtStatus.exists
                                    ? "bg-amber-50 text-amber-700"
                                    : "bg-emerald-50 text-emerald-700"
                                }`}
                              >
                                {courtStatus.courtName}: {courtStatus.exists ? "ya existe" : "se crea"}
                              </span>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {previewSummary.crossesMidnight ? (
                    <p className="mt-3 text-xs font-medium text-amber-700">
                      Algunos turnos terminan después de la medianoche del día seleccionado.
                    </p>
                  ) : null}
                </>
              ) : null}
            </div>

            {bulkError ? (
              <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                <div className="flex items-start gap-2">
                  <CircleAlert className="mt-0.5" size={16} />
                  <span>{bulkError}</span>
                </div>
              </div>
            ) : null}

            {bulkSuccess ? (
              <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                {bulkSuccess}
              </div>
            ) : null}

            <button className="btn-primary w-full" type="submit" disabled={bulkCreateMutation.isPending || existingDayTimeslotsQuery.isLoading}>
              {bulkCreateMutation.isPending ? (
                <span className="inline-flex items-center gap-2">
                  <LoaderCircle className="animate-spin" size={16} />
                  Generando turnos...
                </span>
              ) : (
                <span className="inline-flex items-center gap-2">
                  <Plus size={16} />
                  Crear bloque de turnos
                </span>
              )}
            </button>
          </form>

          <div className="shell-card space-y-4 p-5">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <h3 className="text-lg font-bold text-slate-950">Turnos existentes</h3>
                <p className="text-sm text-slate-500">Filtrá por fecha y cancha, luego elegí uno para editarlo.</p>
              </div>
              <div className="shell-card flex items-center gap-3 px-4 py-3 shadow-none">
                <CalendarClock className="text-skyline" size={18} />
                <input className="bg-transparent text-sm font-semibold text-slate-700" type="date" value={selectedDate} onChange={(event) => setSelectedDate(event.target.value)} />
              </div>
            </div>

            <div>
              <label className="mb-2 block text-sm font-semibold text-slate-700" htmlFor="timeslot-court-filter">
                Filtrar por cancha
              </label>
              <select id="timeslot-court-filter" className="field" value={filterCourtId} onChange={(event) => setFilterCourtId(event.target.value)}>
                <option value="">Todas las canchas</option>
                {courtsQuery.data?.map((court) => (
                  <option key={court.id} value={court.id}>{court.name}</option>
                ))}
              </select>
            </div>

            {editError ? <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{editError}</div> : null}
            {editSuccess ? <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{editSuccess}</div> : null}

            <div className="space-y-3">
              {timeslotsQuery.isLoading ? (
                <LoadingCard label="Cargando turnos..." />
              ) : timeslotsQuery.data?.length ? (
                timeslotsQuery.data.map((timeslot) => {
                  const court = courtsById.get(timeslot.court_id);
                  const isEditing = editingTimeSlotId === timeslot.id;

                  return (
                    <article key={timeslot.id} className="rounded-3xl border border-slate-200 bg-white p-4">
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                        <div>
                          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">{court?.name || "Cancha"}</p>
                          <h4 className="mt-1 text-lg font-bold text-slate-950">{dateLabel(timeslot.starts_at)}</h4>
                          <p className="mt-1 text-sm text-slate-500">Finaliza {dateLabel(timeslot.ends_at)} · Capacidad {timeslot.capacity}</p>
                        </div>
                        <div className="flex items-center gap-2 text-sm font-semibold text-slate-700">
                          <TimerReset size={16} />
                          <span>{timeslot.is_active ? "Activo" : "Inactivo"}</span>
                          <button className="btn-secondary" type="button" onClick={() => beginEdit(timeslot)}>
                            <PencilLine size={16} />
                            Editar
                          </button>
                        </div>
                      </div>

                      {isEditing ? (
                        <form className="mt-4 grid gap-4 border-t border-slate-200 pt-4" onSubmit={handleEditSubmit}>
                          <div className="grid gap-4 sm:grid-cols-2">
                            <input className="field" type="datetime-local" value={editStartsAt} onChange={(event) => setEditStartsAt(event.target.value)} />
                            <input className="field" type="datetime-local" value={editEndsAt} onChange={(event) => setEditEndsAt(event.target.value)} />
                          </div>

                          <div className="grid gap-4 sm:grid-cols-3">
                            <input className="field" type="number" min="1" value={editCapacity} onChange={(event) => setEditCapacity(event.target.value)} />
                            <input className="field" type="number" min="0" step="1" value={editPrice} onChange={(event) => setEditPrice(event.target.value)} placeholder="Precio" />
                            <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                              <input type="checkbox" checked={editIsActive} onChange={(event) => setEditIsActive(event.target.checked)} />
                              Activo
                            </label>
                          </div>

                          <button className="btn-primary" type="submit" disabled={updateTimeSlotMutation.isPending}>
                            {updateTimeSlotMutation.isPending ? (
                              <span className="inline-flex items-center gap-2">
                                <LoaderCircle className="animate-spin" size={16} />
                                Guardando...
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-2">
                                <Save size={16} />
                                Guardar cambios
                              </span>
                            )}
                          </button>
                        </form>
                      ) : null}
                    </article>
                  );
                })
              ) : (
                <EmptyState title="Todavía no hay turnos para este filtro" description="Podés crear un bloque desde la izquierda o cambiar la fecha y la cancha seleccionada." />
              )}
            </div>
          </div>
        </div>
      </section>
    </>
  );
}

