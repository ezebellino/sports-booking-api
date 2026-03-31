import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Calendar1,
  CheckCircle2,
  CircleDollarSign,
  Clock3,
  MapPin,
  MoveRight,
  ShieldAlert,
  Trees,
  Trophy,
  Users,
  X,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { AppHeader } from "../components/app-header";
import { EmptyState } from "../components/empty-state";
import { LoadingCard } from "../components/loading-card";
import { SectionTitle } from "../components/section-title";
import { api, type TimeSlot } from "../lib/api";
import { currency, dateInputDefault, dateLabel, localDateBounds, timeZoneSummary } from "../lib/format";
import { useAuth } from "../modules/auth/auth-context";

export function ExplorePage() {
  const queryClient = useQueryClient();
  const { isAuthenticated } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedDate, setSelectedDate] = useState(dateInputDefault);
  const [feedback, setFeedback] = useState<string | null>(null);
  const dayBounds = useMemo(() => localDateBounds(selectedDate), [selectedDate]);

  const selectedSportId = searchParams.get("sport");
  const selectedVenueId = searchParams.get("venue");
  const selectedCourtId = searchParams.get("court");

  const sportsQuery = useQuery({ queryKey: ["sports"], queryFn: api.listSports });
  const venuesQuery = useQuery({
    queryKey: ["venues", selectedSportId],
    queryFn: () => api.listVenues(selectedSportId),
    enabled: Boolean(sportsQuery.data),
  });
  const courtsQuery = useQuery({
    queryKey: ["courts", selectedVenueId, selectedSportId],
    queryFn: () => api.listCourts({ venueId: selectedVenueId, sportId: selectedSportId }),
    enabled: Boolean(selectedVenueId || selectedSportId),
  });
  const timeslotsQuery = useQuery({
    queryKey: ["timeslots", selectedCourtId, selectedDate],
    queryFn: () =>
      api.listTimeslots({
        courtId: selectedCourtId,
        dateFrom: dayBounds.startIso,
        dateTo: dayBounds.endIso,
      }),
    enabled: Boolean(selectedCourtId),
  });

  const venuesById = useMemo(
    () => new Map((venuesQuery.data ?? []).map((venue) => [venue.id, venue])),
    [venuesQuery.data],
  );
  const sportsById = useMemo(
    () => new Map((sportsQuery.data ?? []).map((sport) => [sport.id, sport])),
    [sportsQuery.data],
  );
  const courtsById = useMemo(
    () => new Map((courtsQuery.data ?? []).map((court) => [court.id, court])),
    [courtsQuery.data],
  );

  const selectedSport = selectedSportId ? sportsById.get(selectedSportId) ?? null : null;
  const selectedVenue = selectedVenueId ? venuesById.get(selectedVenueId) ?? null : null;
  const selectedCourt = selectedCourtId ? courtsById.get(selectedCourtId) ?? null : null;

  useEffect(() => {
    setFeedback(null);
  }, [selectedSportId, selectedVenueId, selectedCourtId, selectedDate]);

  const bookingMutation = useMutation({
    mutationFn: api.createBooking,
    onSuccess: () => {
      setFeedback("Reserva confirmada. Ya la podés ver en Mis reservas.");
      void queryClient.invalidateQueries({ queryKey: ["bookings"] });
      void queryClient.invalidateQueries({ queryKey: ["timeslots"] });
    },
    onError: (error) => {
      setFeedback(error instanceof Error ? error.message : "No pudimos crear la reserva");
    },
  });

  function updateSelection(key: "sport" | "venue" | "court", value: string | null) {
    const next = new URLSearchParams(searchParams);

    if (value) {
      next.set(key, value);
    } else {
      next.delete(key);
    }

    if (key === "sport") {
      next.delete("venue");
      next.delete("court");
    }

    if (key === "venue") {
      next.delete("court");
    }

    setSearchParams(next);
  }

  const progress = [selectedSport, selectedVenue, selectedCourt].filter(Boolean).length;

  return (
    <>
      <AppHeader />

      <section className="space-y-6">
        <SectionTitle
          eyebrow="Explorar"
          title="Elegí deporte, sede y horario"
          description="El flujo está ordenado para celular: primero el deporte, después la sede, luego la cancha y por último los turnos disponibles para la fecha elegida. Los horarios se muestran en la hora local de cada sede."
          action={
            <div className="shell-card flex items-center gap-3 px-4 py-3">
              <Calendar1 className="text-skyline" size={18} />
              <input
                className="bg-transparent text-sm font-semibold text-slate-700"
                type="date"
                value={selectedDate}
                onChange={(event) => setSelectedDate(event.target.value)}
              />
            </div>
          }
        />

        <div className="shell-card sticky top-3 z-10 border border-slate-200/80 bg-white/95 p-4 backdrop-blur">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">Progreso de reserva</p>
              <h3 className="mt-1 text-lg font-bold text-slate-950">{progress}/3 pasos completos antes de ver turnos</h3>
              <p className="mt-1 text-sm text-slate-500">
                Mantenemos visible tu contexto para que no te pierdas al bajar por la pantalla.
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              <SelectionBadge label="Deporte" value={selectedSport?.name} onClear={() => updateSelection("sport", null)} />
              <SelectionBadge label="Sede" value={selectedVenue?.name} onClear={() => updateSelection("venue", null)} />
              <SelectionBadge label="Cancha" value={selectedCourt?.name} onClear={() => updateSelection("court", null)} />
            </div>
          </div>
        </div>

        {feedback ? (
          <div
            className={`shell-card flex items-start gap-3 p-4 text-sm ${
              bookingMutation.isError
                ? "border-rose-200 bg-rose-50 text-rose-800"
                : "border-emerald-200 bg-emerald-50 text-emerald-800"
            }`}
          >
            {bookingMutation.isError ? <ShieldAlert size={18} /> : <CheckCircle2 size={18} />}
            <div>
              <p className="font-semibold">{bookingMutation.isError ? "No pudimos reservar" : "Reserva creada"}</p>
              <p className="mt-1">{feedback}</p>
            </div>
          </div>
        ) : null}

        <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
          <div className="space-y-4">
            <section className="shell-card p-5">
              <FilterTitle icon={Trophy} title="1. Deporte" subtitle="Elegí qué querés jugar" />
              {sportsQuery.isLoading ? (
                <LoadingCard label="Cargando deportes..." />
              ) : (
                <div className="mt-4 flex flex-wrap gap-2">
                  {sportsQuery.data?.map((sport) => (
                    <button
                      key={sport.id}
                      className={`chip ${selectedSportId === sport.id ? "chip-active" : ""}`}
                      type="button"
                      onClick={() => updateSelection("sport", selectedSportId === sport.id ? null : sport.id)}
                    >
                      {sport.name}
                    </button>
                  ))}
                </div>
              )}
            </section>

            <section className="shell-card p-5">
              <FilterTitle icon={MapPin} title="2. Sede" subtitle="Filtrada según el deporte elegido" />
              {!selectedSportId ? (
                <StepHint message="Elegí un deporte para ver solo las sedes que aplican a esa búsqueda." />
              ) : venuesQuery.isLoading ? (
                <LoadingCard label="Buscando sedes..." />
              ) : venuesQuery.data?.length ? (
                <div className="mt-4 grid gap-3">
                  {venuesQuery.data.map((venue) => (
                    <button
                      key={venue.id}
                      className={`rounded-3xl border p-4 text-left transition ${
                        selectedVenueId === venue.id
                          ? "border-slate-900 bg-slate-900 text-white"
                          : "border-slate-200 bg-white hover:border-slate-300"
                      }`}
                      type="button"
                      onClick={() => updateSelection("venue", selectedVenueId === venue.id ? null : venue.id)}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-sm font-bold">{venue.name}</p>
                          <p className="mt-1 text-sm opacity-80">{venue.address || "Dirección pendiente"}</p>
                        </div>
                        {selectedVenueId === venue.id ? <CheckCircle2 size={18} /> : null}
                      </div>
                    </button>
                  ))}
                </div>
              ) : (
                <StepHint message="No hay sedes disponibles para ese deporte todavía." tone="muted" />
              )}
            </section>
          </div>

          <div className="space-y-4">
            <section className="shell-card p-5">
              <FilterTitle icon={Trees} title="3. Cancha" subtitle="Elegí dónde querés reservar" />
              {!selectedVenueId ? (
                <StepHint message="Primero seleccioná una sede para ver sus canchas disponibles." />
              ) : courtsQuery.isLoading ? (
                <LoadingCard label="Cargando canchas..." />
              ) : courtsQuery.data?.length ? (
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  {courtsQuery.data.map((court) => (
                    <button
                      key={court.id}
                      className={`rounded-3xl border p-4 text-left transition ${
                        selectedCourtId === court.id
                          ? "border-transparent bg-orange-500 text-white shadow-soft"
                          : "border-slate-200 bg-white hover:border-slate-300"
                      }`}
                      type="button"
                      onClick={() => updateSelection("court", selectedCourtId === court.id ? null : court.id)}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-sm font-bold">{court.name}</p>
                          <p className="mt-1 text-xs font-semibold uppercase tracking-[0.18em] opacity-80">
                            {court.indoor ? "Indoor" : "Outdoor"} · {court.is_active ? "Activa" : "Inactiva"}
                          </p>
                        </div>
                        {selectedCourtId === court.id ? <CheckCircle2 size={18} /> : null}
                      </div>
                    </button>
                  ))}
                </div>
              ) : (
                <StepHint message="No hay canchas cargadas para esta combinación de sede y deporte." tone="muted" />
              )}
            </section>

            <section className="shell-card p-5">
              <FilterTitle icon={CircleDollarSign} title="4. Turnos" subtitle="Solo mostramos lo que coincide con tu selección actual" />
              {!selectedCourtId ? (
                <EmptyState
                  title="Todavía no elegiste una cancha"
                  description="Apenas selecciones una cancha vamos a consultar los turnos disponibles para la fecha elegida."
                />
              ) : timeslotsQuery.isLoading ? (
                <LoadingCard label="Buscando turnos..." />
              ) : timeslotsQuery.data?.length ? (
                <div className="mt-4 space-y-3">
                  {timeslotsQuery.data.map((slot) => {
                    const court = courtsById.get(slot.court_id);
                    const sport = court ? sportsById.get(court.sport_id) : null;
                    const venue = court ? venuesById.get(court.venue_id) : null;
                    const isBookable = slot.availability_status === "available" || slot.availability_status === "few_left";
                    const bookingPending = bookingMutation.isPending && bookingMutation.variables === slot.id;

                    return (
                      <article key={slot.id} className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
                        <div className="flex flex-col gap-4">
                          <div className="flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
                            <span>{sport?.name || "Deporte"}</span>
                            <MoveRight size={14} />
                            <span>{venue?.name || "Sede"}</span>
                          </div>

                          <div className="flex flex-col gap-3 rounded-2xl bg-slate-50 p-3 text-sm text-slate-600 sm:flex-row sm:items-center sm:justify-between">
                            <div className="flex items-center gap-2">
                              <Users size={16} className="text-slate-500" />
                              <span>
                                {slot.confirmed_bookings}/{slot.capacity} reservados · {slot.remaining_spots} disponibles
                              </span>
                            </div>
                            <AvailabilityBadge slot={slot} />
                          </div>

                          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                            <div>
                              <h3 className="text-lg font-bold text-slate-950">{court?.name || "Cancha"}</h3>
                              <div className="mt-2 flex items-center gap-2 text-sm text-slate-500">
                                <Clock3 size={16} />
                                <span>{dateLabel(slot.starts_at, venue?.timezone)}</span>
                              </div>
                              <p className="mt-2 text-sm text-slate-500">{availabilityMessage(slot)}</p>`r`n                              <p className="mt-1 text-xs font-medium text-slate-400">Hora local de la sede: {timeZoneSummary(venue?.timezone)}</p>
                              <p className="mt-2 text-base font-semibold text-slate-900">{currency(slot.price)}</p>
                            </div>

                            {isAuthenticated ? (
                              <button
                                className={isBookable ? "btn-primary" : "btn-secondary opacity-60"}
                                type="button"
                                onClick={() => bookingMutation.mutate(slot.id)}
                                disabled={bookingPending || !isBookable}
                              >
                                {bookingPending ? "Reservando..." : isBookable ? "Reservar" : buttonLabel(slot)}
                              </button>
                            ) : (
                              <Link className="btn-secondary" to="/login">
                                Ingresá para reservar
                              </Link>
                            )}
                          </div>
                        </div>
                      </article>
                    );
                  })}
                </div>
              ) : (
                <EmptyState
                  title="Sin turnos para esa fecha"
                  description="Probá con otra fecha o cargá más turnos desde el panel admin."
                />
              )}
            </section>
          </div>
        </div>
      </section>
    </>
  );
}

function FilterTitle({
  icon: Icon,
  title,
  subtitle,
}: {
  icon: LucideIcon;
  title: string;
  subtitle: string;
}) {
  return (
    <div className="flex items-center gap-3">
      <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-100 text-slate-700">
        <Icon size={18} />
      </div>
      <div>
        <h3 className="text-lg font-bold text-slate-950">{title}</h3>
        <p className="text-sm text-slate-500">{subtitle}</p>
      </div>
    </div>
  );
}

function SelectionBadge({
  label,
  value,
  onClear,
}: {
  label: string;
  value?: string | null;
  onClear: () => void;
}) {
  if (!value) {
    return (
      <span className="inline-flex items-center rounded-full border border-dashed border-slate-300 px-3 py-2 text-xs font-semibold text-slate-400">
        {label}: pendiente
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-2 rounded-full bg-slate-900 px-3 py-2 text-xs font-semibold text-white">
      <span>
        {label}: {value}
      </span>
      <button
        type="button"
        className="rounded-full bg-white/10 p-1 text-white/80 transition hover:bg-white/20"
        onClick={onClear}
        aria-label={`Limpiar ${label}`}
      >
        <X size={12} />
      </button>
    </span>
  );
}

function StepHint({ message, tone = "default" }: { message: string; tone?: "default" | "muted" }) {
  return (
    <div
      className={`mt-4 rounded-2xl border px-4 py-3 text-sm ${
        tone === "muted"
          ? "border-slate-200 bg-slate-50 text-slate-500"
          : "border-sky-100 bg-sky-50 text-sky-900"
      }`}
    >
      {message}
    </div>
  );
}

function AvailabilityBadge({ slot }: { slot: TimeSlot }) {
  const styles = {
    available: "bg-emerald-100 text-emerald-800",
    few_left: "bg-amber-100 text-amber-800",
    full: "bg-rose-100 text-rose-800",
    inactive: "bg-slate-200 text-slate-600",
    expired: "bg-slate-200 text-slate-600",
  }[slot.availability_status];

  return <span className={`rounded-full px-3 py-1 text-xs font-semibold ${styles}`}>{availabilityLabel(slot)}</span>;
}

function availabilityLabel(slot: TimeSlot) {
  switch (slot.availability_status) {
    case "few_left":
      return "Pocos lugares";
    case "full":
      return "Completo";
    case "inactive":
      return "Inactivo";
    case "expired":
      return "Vencido";
    default:
      return "Disponible";
  }
}

function availabilityMessage(slot: TimeSlot) {
  switch (slot.availability_status) {
    case "few_left":
      return `Quedan ${slot.remaining_spots} lugar${slot.remaining_spots === 1 ? "" : "es"}.`;
    case "full":
      return "No quedan cupos para este horario.";
    case "inactive":
      return "Este turno está inactivo por el momento.";
    case "expired":
      return "Este turno ya pasó y queda solo como referencia.";
    default:
      return `Hay ${slot.remaining_spots} lugares disponibles en este turno.`;
  }
}

function buttonLabel(slot: TimeSlot) {
  switch (slot.availability_status) {
    case "full":
      return "Completo";
    case "inactive":
      return "Inactivo";
    case "expired":
      return "Vencido";
    default:
      return "Reservar";
  }
}

