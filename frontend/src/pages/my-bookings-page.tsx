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

  if (bookingsQuery.isLoading) {
    return (
      <>
        <AppHeader />
        <LoadingCard label="Armando tu agenda..." />
      </>
    );
  }

  return (
    <>
      <AppHeader />
      <section className="space-y-6">
        <SectionTitle
          eyebrow="Agenda"
          title="Tus reservas"
          description="Ahora esta vista consume un payload de reservas enriquecido desde backend, así que la UI puede mostrar la información útil sin reconstruir relaciones del lado cliente."
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
              const timeslot = booking.timeslot;
              const court = timeslot.court;
              const sport = court.sport;
              const venue = court.venue;

              return (
                <article key={booking.id} className="shell-card p-5">
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-skyline">
                    {booking.status}
                  </p>
                  <h3 className="mt-2 text-xl font-bold text-slate-950">
                    {court.name} · {sport.name}
                  </h3>
                  <p className="mt-2 text-sm text-slate-500">{venue.name}</p>
                  <p className="mt-1 text-sm font-semibold text-slate-800">
                    {dateLabel(timeslot.starts_at)}
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