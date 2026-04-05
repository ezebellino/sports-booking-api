import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BellRing, CalendarClock, CalendarX2, CircleAlert, LoaderCircle, Save } from "lucide-react";
import { Link } from "react-router-dom";
import { AppHeader } from "../components/app-header";
import { EmptyState } from "../components/empty-state";
import { LoadingCard } from "../components/loading-card";
import { SectionTitle } from "../components/section-title";
import { api } from "../lib/api";
import { dateLabel, timeZoneSummary } from "../lib/format";
import { normalizePhone, validateWhatsappNumber } from "../lib/validation";
import { useAuth } from "../modules/auth/auth-context";
import { useEffect, useState } from "react";

export function MyBookingsPage() {
  const queryClient = useQueryClient();
  const { user, updateProfile } = useAuth();
  const bookingsQuery = useQuery({ queryKey: ["bookings"], queryFn: api.listBookings });
  const policiesQuery = useQuery({ queryKey: ["booking-policies"], queryFn: () => api.listBookingPolicies() });
  const notificationStatusQuery = useQuery({
    queryKey: ["notification-status"],
    queryFn: api.getNotificationStatus,
    enabled: user?.role === "admin",
  });
  const [whatsappNumber, setWhatsappNumber] = useState(user?.whatsapp_number ?? "");
  const [whatsappOptIn, setWhatsappOptIn] = useState(user?.whatsapp_opt_in ?? false);
  const [whatsappError, setWhatsappError] = useState<string | null>(null);

  useEffect(() => {
    setWhatsappNumber(user?.whatsapp_number ?? "");
    setWhatsappOptIn(user?.whatsapp_opt_in ?? false);
  }, [user?.whatsapp_number, user?.whatsapp_opt_in]);

  const cancelBookingMutation = useMutation({
    mutationFn: api.cancelBooking,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["bookings"] });
      void queryClient.invalidateQueries({ queryKey: ["timeslots"] });
    },
  });

  const updateWhatsappMutation = useMutation({
    mutationFn: async () => {
      const phoneError = validateWhatsappNumber(whatsappNumber);
      if (phoneError) {
        throw new Error(phoneError);
      }
      await updateProfile({
        whatsapp_number: normalizePhone(whatsappNumber) || null,
        whatsapp_opt_in: whatsappOptIn,
      });
    },
    onSuccess: () => {
      setWhatsappError(null);
    },
    onError: (error) => {
      setWhatsappError(error instanceof Error ? error.message : "No pudimos guardar tu WhatsApp.");
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
              <p className="font-semibold text-slate-900">Cómo funcionan las cancelaciones</p>
              <p className="mt-1">{policiesQuery.data.cancellation_message}</p>
              <p className="mt-2 text-xs font-medium text-slate-400">
                Si reservás distintos deportes, cada tarjeta te muestra la política exacta que aplica a ese turno.
              </p>
            </div>
          </div>
        ) : null}

        <div className="shell-card p-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-700">
              <BellRing size={18} />
            </div>
            <div>
              <h3 className="text-lg font-bold text-slate-950">Notificaciones por WhatsApp</h3>
              <p className="text-sm text-slate-500">
                Guardá tu número para recibir avisos automáticos cuando se confirme o cancele una reserva.
              </p>
            </div>
          </div>

          <div className="mt-4 grid gap-4 sm:grid-cols-[1fr_auto]">
            <div>
              <label className="mb-2 block text-sm font-semibold text-slate-700" htmlFor="agenda-whatsapp">
                Número de WhatsApp
              </label>
              <input
                id="agenda-whatsapp"
                className="field"
                type="tel"
                placeholder="5491122334455"
                value={whatsappNumber}
                onChange={(event) => {
                  setWhatsappNumber(event.target.value);
                  setWhatsappError(null);
                }}
              />
            </div>
            <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700 sm:self-end">
              <input
                type="checkbox"
                checked={whatsappOptIn}
                onChange={(event) => setWhatsappOptIn(event.target.checked)}
              />
              Recibir avisos
            </label>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button className="btn-primary" type="button" onClick={() => updateWhatsappMutation.mutate()} disabled={updateWhatsappMutation.isPending}>
              {updateWhatsappMutation.isPending ? (
                <span className="inline-flex items-center gap-2">
                  <LoaderCircle className="animate-spin" size={16} />
                  Guardando...
                </span>
              ) : (
                <span className="inline-flex items-center gap-2">
                  <Save size={16} />
                  Guardar WhatsApp
                </span>
              )}
            </button>
            <p className="text-sm text-slate-500">
              {user?.whatsapp_opt_in && user.whatsapp_number
                ? "Las notificaciones están activas para tu cuenta."
                : "Todavía no hay un WhatsApp activo para avisos automáticos."}
            </p>
          </div>

          {whatsappError ? (
            <div className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              <div className="flex items-start gap-2">
                <CircleAlert className="mt-0.5" size={16} />
                <span>{whatsappError}</span>
              </div>
            </div>
          ) : null}

          {user?.role === "admin" && notificationStatusQuery.data ? (
            <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
              <p className="font-semibold text-slate-900">Estado técnico de la integración</p>
              <p className="mt-1">Proveedor: {notificationStatusQuery.data.provider}</p>
              <p className="mt-1">
                {notificationStatusQuery.data.configured
                  ? "La integración está lista para enviar mensajes template."
                  : "Faltan credenciales o configuración para habilitar el envío real."}
              </p>
            </div>
          ) : null}
        </div>

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
                        <>
                          {booking.booking_policy_summary ? (
                            <p className="mt-2 text-xs font-medium text-slate-400">{booking.booking_policy_summary}</p>
                          ) : null}
                          <p className="mt-1 text-xs text-slate-500">
                            {booking.can_cancel && booking.cancellation_deadline
                              ? `Podés cancelar hasta ${dateLabel(booking.cancellation_deadline, venue.timezone)}.`
                              : booking.cancellation_policy_message}
                          </p>
                        </>
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
                        {isCancelling ? "Cancelando..." : booking.can_cancel ? "Cancelar reserva" : "Ventana cerrada"}
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
