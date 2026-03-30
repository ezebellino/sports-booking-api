import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Calendar1, CircleDollarSign, MapPin, Trees, Trophy } from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { AppHeader } from "../components/app-header";
import { EmptyState } from "../components/empty-state";
import { LoadingCard } from "../components/loading-card";
import { SectionTitle } from "../components/section-title";
import { api } from "../lib/api";
import { currency, dateInputDefault, dateLabel } from "../lib/format";
import { useAuth } from "../modules/auth/auth-context";

export function ExplorePage() {
  const queryClient = useQueryClient();
  const { isAuthenticated } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedDate, setSelectedDate] = useState(dateInputDefault);
  const [feedback, setFeedback] = useState<string | null>(null);

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
        dateFrom: `${selectedDate}T00:00:00`,
        dateTo: `${selectedDate}T23:59:59`,
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

  const bookingMutation = useMutation({
    mutationFn: api.createBooking,
    onSuccess: () => {
      setFeedback("Reserva confirmada. Ya la podés ver en Mis reservas.");
      void queryClient.invalidateQueries({ queryKey: ["bookings"] });
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

  return (
    <>
      <AppHeader />

      <section className="space-y-6">
        <SectionTitle
          eyebrow="Explorar"
          title="Elegí deporte, sede y horario"
          description="Este flujo orquesta tus recursos actuales para que la reserva se sienta simple en mobile. Empezá por un deporte y el resto de filtros se va acomodando."
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

        {feedback ? (
          <div className="shell-card border-sky-100 bg-sky-50 p-4 text-sm text-sky-900">
            {feedback}
          </div>
        ) : null}

        <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
          <div className="space-y-4">
            <div className="shell-card p-5">
              <FilterTitle icon={<Trophy size={18} />} title="1. Deporte" />
              {sportsQuery.isLoading ? (
                <LoadingCard label="Cargando deportes..." />
              ) : (
                <div className="mt-4 flex flex-wrap gap-2">
                  {sportsQuery.data?.map((sport) => (
                    <button
                      key={sport.id}
                      className={`chip ${selectedSportId === sport.id ? "chip-active" : ""}`}
                      type="button"
                      onClick={() =>
                        updateSelection("sport", selectedSportId === sport.id ? null : sport.id)
                      }
                    >
                      {sport.name}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div className="shell-card p-5">
              <FilterTitle icon={<MapPin size={18} />} title="2. Sede" />
              {!selectedSportId ? (
                <p className="mt-4 text-sm text-slate-500">Elegí un deporte para filtrar sedes.</p>
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
                      onClick={() =>
                        updateSelection("venue", selectedVenueId === venue.id ? null : venue.id)
                      }
                    >
                      <p className="text-sm font-bold">{venue.name}</p>
                      <p className="mt-1 text-sm opacity-80">
                        {venue.address || "Dirección pendiente"}
                      </p>
                    </button>
                  ))}
                </div>
              ) : (
                <p className="mt-4 text-sm text-slate-500">No hay sedes para este deporte todavía.</p>
              )}
            </div>
          </div>

          <div className="space-y-4">
            <div className="shell-card p-5">
              <FilterTitle icon={<Trees size={18} />} title="3. Cancha" />
              {!selectedVenueId ? (
                <p className="mt-4 text-sm text-slate-500">Elegí una sede para ver las canchas.</p>
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
                      onClick={() =>
                        updateSelection("court", selectedCourtId === court.id ? null : court.id)
                      }
                    >
                      <p className="text-sm font-bold">{court.name}</p>
                      <p className="mt-1 text-xs font-semibold uppercase tracking-[0.18em] opacity-80">
                        {court.indoor ? "Indoor" : "Outdoor"} · {court.is_active ? "Activa" : "Inactiva"}
                      </p>
                    </button>
                  ))}
                </div>
              ) : (
                <p className="mt-4 text-sm text-slate-500">
                  No hay canchas cargadas para esta combinación.
                </p>
              )}
            </div>

            <div className="shell-card p-5">
              <FilterTitle icon={<CircleDollarSign size={18} />} title="4. Turnos" />
              {!selectedCourtId ? (
                <EmptyState
                  title="Todavía no elegiste una cancha"
                  description="Apenas selecciones una cancha vamos a consultar `/timeslots` para la fecha elegida."
                />
              ) : timeslotsQuery.isLoading ? (
                <LoadingCard label="Buscando turnos..." />
              ) : timeslotsQuery.data?.length ? (
                <div className="mt-4 space-y-3">
                  {timeslotsQuery.data.map((slot) => {
                    const court = courtsById.get(slot.court_id);
                    const sport = court ? sportsById.get(court.sport_id) : null;
                    const venue = court ? venuesById.get(court.venue_id) : null;

                    return (
                      <article
                        key={slot.id}
                        className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm"
                      >
                        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                          <div>
                            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">
                              {sport?.name || "Deporte"} · {venue?.name || "Sede"}
                            </p>
                            <h3 className="mt-1 text-lg font-bold text-slate-950">
                              {court?.name || "Cancha"}
                            </h3>
                            <p className="mt-2 text-sm text-slate-500">{dateLabel(slot.starts_at)}</p>
                            <p className="mt-1 text-sm font-semibold text-slate-800">
                              {currency(slot.price)}
                            </p>
                          </div>

                          {isAuthenticated ? (
                            <button
                              className="btn-primary"
                              type="button"
                              onClick={() => bookingMutation.mutate(slot.id)}
                              disabled={bookingMutation.isPending}
                            >
                              {bookingMutation.isPending ? "Reservando..." : "Reservar"}
                            </button>
                          ) : (
                            <Link className="btn-secondary" to="/login">
                              Ingresá para reservar
                            </Link>
                          )}
                        </div>
                      </article>
                    );
                  })}
                </div>
              ) : (
                <EmptyState
                  title="Sin turnos para esa fecha"
                  description="Probá con otra fecha o cargá más timeslots desde el backend."
                />
              )}
            </div>
          </div>
        </div>
      </section>
    </>
  );
}

function FilterTitle({ icon, title }: { icon: ReactNode; title: string }) {
  return (
    <div className="flex items-center gap-3">
      <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-100 text-slate-700">
        {icon}
      </div>
      <div>
        <h3 className="text-lg font-bold text-slate-950">{title}</h3>
      </div>
    </div>
  );
}
