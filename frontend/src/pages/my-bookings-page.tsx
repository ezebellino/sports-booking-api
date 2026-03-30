import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { AppHeader } from "../components/app-header";
import { EmptyState } from "../components/empty-state";
import { LoadingCard } from "../components/loading-card";
import { SectionTitle } from "../components/section-title";
import { api } from "../lib/api";
import { dateLabel } from "../lib/format";

export function MyBookingsPage() {
  const bookingsQuery = useQuery({ queryKey: ["bookings"], queryFn: api.listBookings });
  const sportsQuery = useQuery({ queryKey: ["sports"], queryFn: api.listSports });
  const venuesQuery = useQuery({ queryKey: ["venues"], queryFn: () => api.listVenues(null) });
  const courtsQuery = useQuery({
    queryKey: ["courts", "all"],
    queryFn: () => api.listCourts({}),
  });
  const timeslotsQuery = useQuery({
    queryKey: ["timeslots", "all"],
    queryFn: () => api.listTimeslots({}),
  });

  if (
    bookingsQuery.isLoading ||
    sportsQuery.isLoading ||
    venuesQuery.isLoading ||
    courtsQuery.isLoading ||
    timeslotsQuery.isLoading
  ) {
    return (
      <>
        <AppHeader />
        <LoadingCard label="Armando tu agenda..." />
      </>
    );
  }

  const sportsById = new Map((sportsQuery.data ?? []).map((sport) => [sport.id, sport]));
  const venuesById = new Map((venuesQuery.data ?? []).map((venue) => [venue.id, venue]));
  const courtsById = new Map((courtsQuery.data ?? []).map((court) => [court.id, court]));
  const timeslotsById = new Map((timeslotsQuery.data ?? []).map((timeslot) => [timeslot.id, timeslot]));

  return (
    <>
      <AppHeader />
      <section className="space-y-6">
        <SectionTitle
          eyebrow="Agenda"
          title="Tus reservas"
          description="Esta vista resuelve el join en el frontend usando tus endpoints actuales, para que el usuario vea algo entendible aunque `/bookings` todavía devuelva solo IDs."
        />

        {!bookingsQuery.data?.length ? (
          <EmptyState
            title="Todavía no hay reservas"
            description="Cuando reserves un turno desde Explorar, va a aparecer acá con su cancha y horario."
            action={
              <Link className="btn-primary" to="/explore">
                Buscar turnos
              </Link>
            }
          />
        ) : (
          <div className="grid gap-4">
            {bookingsQuery.data.map((booking) => {
              const timeslot = timeslotsById.get(booking.timeslot_id);
              const court = timeslot ? courtsById.get(timeslot.court_id) : null;
              const sport = court ? sportsById.get(court.sport_id) : null;
              const venue = court ? venuesById.get(court.venue_id) : null;

              return (
                <article key={booking.id} className="shell-card p-5">
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-skyline">
                    {booking.status}
                  </p>
                  <h3 className="mt-2 text-xl font-bold text-slate-950">
                    {court?.name || "Cancha"} · {sport?.name || "Deporte"}
                  </h3>
                  <p className="mt-2 text-sm text-slate-500">{venue?.name || "Sede"}</p>
                  <p className="mt-1 text-sm font-semibold text-slate-800">
                    {timeslot ? dateLabel(timeslot.starts_at) : "Horario no disponible"}
                  </p>
                </article>
              );
            })}
          </div>
        )}
      </section>
    </>
  );
}
