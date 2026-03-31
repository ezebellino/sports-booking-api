import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarClock, CalendarX2 } from "lucide-react";
import { Link } from "react-router-dom";
import { AppHeader } from "../components/app-header";
import { EmptyState } from "../components/empty-state";
import { LoadingCard } from "../components/loading-card";
import { SectionTitle } from "../components/section-title";
import { api } from "../lib/api";
import { dateLabel, timeZoneSummary } from "../lib/format";

export function MyBookingsPage() {
  const queryClient = useQueryClient();
  const bookingsQuery = useQuery({ queryKey: ["bookings"], queryFn: api.listBookings });
  const policiesQuery = useQuery({ queryKey: ["booking-policies"], queryFn: api.listBookingPolicies });

  const cancelBookingMutation = useMutation({
    mutationFn: api.cancelBooking,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["bookings"] });
      void queryClient.invalidateQueries({ queryKey: ["timeslots"] });
    },
  });

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
          description="Acá podés revisar tu historial, ver el estado de cada reserva y cancelar las que ya no vayas a usar. Los horarios se muestran en la hora local de cada sede."
        />

        {policiesQuery.data ? (
          <div className="shell-card flex items-start gap-3 p-4 text-sm text-slate-600">
            <CalendarClock className="mt-0.5 text-skyline" size={18} />
            <div>
              <p className="font-semibold text-slate-900">Política actual de reservas</p>
              <p className="mt-1">{policiesQuery.data.cancellation_message}</p>
            </div>
          </div>
        ) : null}

        {!bookingsQuery.data?.length ? (
          <EmptyState
            title="Todavía no hay reservas"
            description="Cuando reserves un turno desde Explorar, va a aparecer acá con su cancha, horario y estado."
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
              const isCancelled = booking.status === "cancelled";
              const isCancelling = cancelBookingMutation.isPending && cancelBookingMutation.variables === booking.id;

              return (
                <article key={booking.id} className="shell-card p-5">
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <div className="flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em]">
                        <span className={isCancelled ? "text-slate-400" : "text-skyline"}>{booking.status}</span>
                        <span className="text-slate-300">•</span>
                        <span className="text-slate-400">{venue.name}</span>
                      </div>
                      <h3 className="mt-2 text-xl font-bold text-slate-950">
                        {court.name} · {sport.name}
                      </h3>
                      <p className="mt-2 text-sm text-slate-500">{dateLabel(timeslot.starts_at, venue.timezone)}</p>
                      <p className="mt-1 text-xs font-medium text-slate-400">Hora local de la sede: {timeZoneSummary(venue.timezone)}</p>
                      {!isCancelled ? (
                        <p className="mt-2 text-xs text-slate-500">
                          {booking.can_cancel && booking.cancellation_deadline
                            ? `Podés cancelar hasta ${dateLabel(booking.cancellation_deadline, venue.timezone)}.`
                            : booking.cancellation_policy_message}
                        </p>
                      ) : null}
                    </div>

                    {isCancelled ? (
                      <span className="inline-flex items-center rounded-full bg-slate-100 px-3 py-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                        Cancelada
                      </span>
                    ) : (
                      <button
                        className={`btn-secondary ${booking.can_cancel ? "text-rose-700" : "opacity-60"}`}
                        type="button"
                        onClick={() => cancelBookingMutation.mutate(booking.id)}
                        disabled={isCancelling || !booking.can_cancel}
                      >
                        <CalendarX2 size={16} />
                        {isCancelling ? "Cancelando..." : booking.can_cancel ? "Cancelar reserva" : "Cancelación cerrada"}
                      </button>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>
    </>
  );
}
