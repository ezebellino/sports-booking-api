import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CircleAlert, LoaderCircle, PencilLine, Save, TimerReset } from "lucide-react";
import { useState } from "react";
import { api } from "../lib/api";
import { EmptyState } from "./empty-state";
import { LoadingCard } from "./loading-card";

function normalizeOptionalText(value: string) {
  const trimmed = value.trim();
  return trimmed.length ? trimmed : null;
}

function normalizeOptionalNumber(value: string) {
  const trimmed = value.trim();
  if (!trimmed.length) {
    return null;
  }
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
}

export function AdminSportPolicies() {
  const queryClient = useQueryClient();
  const [editingSportId, setEditingSportId] = useState<string | null>(null);
  const [editSportDescription, setEditSportDescription] = useState("");
  const [editSportBookingLead, setEditSportBookingLead] = useState("");
  const [editSportCancellationLead, setEditSportCancellationLead] = useState("");
  const [feedback, setFeedback] = useState<{ tone: "error" | "success"; message: string } | null>(null);

  const sportsQuery = useQuery({
    queryKey: ["sports"],
    queryFn: api.listSports,
  });

  const generalPoliciesQuery = useQuery({
    queryKey: ["booking-policies", "general"],
    queryFn: () => api.listBookingPolicies(),
  });

  const updateSportMutation = useMutation({
    mutationFn: ({ sportId, payload }: { sportId: string; payload: Parameters<typeof api.updateSport>[1] }) =>
      api.updateSport(sportId, payload),
    onSuccess: () => {
      setFeedback({ tone: "success", message: "Política del deporte actualizada correctamente." });
      setEditingSportId(null);
      void queryClient.invalidateQueries({ queryKey: ["sports"] });
      void queryClient.invalidateQueries({ queryKey: ["booking-policies"] });
      void queryClient.invalidateQueries({ queryKey: ["timeslots"] });
      void queryClient.invalidateQueries({ queryKey: ["bookings"] });
    },
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: error instanceof Error ? error.message : "No pudimos actualizar la política del deporte.",
      });
    },
  });

  function startSportEdit(sportId: string) {
    const sport = (sportsQuery.data ?? []).find((item) => item.id === sportId);
    if (!sport) {
      return;
    }
    setEditingSportId(sportId);
    setEditSportDescription(sport.description ?? "");
    setEditSportBookingLead(sport.booking_min_lead_minutes !== null ? String(sport.booking_min_lead_minutes) : "");
    setEditSportCancellationLead(
      sport.cancellation_min_lead_minutes !== null ? String(sport.cancellation_min_lead_minutes) : "",
    );
    setFeedback(null);
  }

  function handleUpdateSport(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editingSportId) {
      return;
    }

    const bookingMinutes = normalizeOptionalNumber(editSportBookingLead);
    const cancellationMinutes = normalizeOptionalNumber(editSportCancellationLead);

    if (editSportBookingLead.trim() && bookingMinutes === null) {
      setFeedback({ tone: "error", message: "La ventana de reserva debe ser numérica." });
      return;
    }

    if (editSportCancellationLead.trim() && cancellationMinutes === null) {
      setFeedback({ tone: "error", message: "La ventana de cancelación debe ser numérica." });
      return;
    }

    updateSportMutation.mutate({
      sportId: editingSportId,
      payload: {
        description: normalizeOptionalText(editSportDescription),
        booking_min_lead_minutes: bookingMinutes,
        cancellation_min_lead_minutes: cancellationMinutes,
      },
    });
  }

  return (
    <div className="shell-card p-5">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-violet-100 text-violet-700">
          <TimerReset size={18} />
        </div>
        <div>
          <h3 className="text-lg font-bold text-slate-950">Políticas por deporte</h3>
          <p className="text-sm text-slate-500">
            Definí cuánto antes se puede reservar o cancelar cada disciplina. Si dejás un valor vacío,
            ese deporte hereda la política general.
          </p>
        </div>
      </div>

      {generalPoliciesQuery.data ? (
        <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
          <p className="font-semibold text-slate-900">Política general actual</p>
          <p className="mt-1">{generalPoliciesQuery.data.booking_message}</p>
          <p className="mt-1">{generalPoliciesQuery.data.cancellation_message}</p>
        </div>
      ) : null}

      {feedback ? (
        <div className={`mt-4 rounded-2xl border px-4 py-3 text-sm ${feedback.tone === "error" ? "border-rose-200 bg-rose-50 text-rose-700" : "border-emerald-200 bg-emerald-50 text-emerald-700"}`}>
          <div className="flex items-start gap-2">
            {feedback.tone === "error" ? <CircleAlert className="mt-0.5" size={16} /> : <Save className="mt-0.5" size={16} />}
            <span>{feedback.message}</span>
          </div>
        </div>
      ) : null}

      {sportsQuery.isLoading ? (
        <div className="mt-4">
          <LoadingCard label="Cargando deportes..." />
        </div>
      ) : (sportsQuery.data ?? []).length ? (
        <div className="mt-4 space-y-3">
          {(sportsQuery.data ?? []).map((sport) => {
            const isEditing = editingSportId === sport.id;
            const bookingText =
              sport.booking_min_lead_minutes !== null
                ? `${sport.booking_min_lead_minutes} min antes`
                : generalPoliciesQuery.data
                  ? `General (${generalPoliciesQuery.data.min_booking_lead_minutes} min)`
                  : "General";
            const cancellationText =
              sport.cancellation_min_lead_minutes !== null
                ? `${sport.cancellation_min_lead_minutes} min antes`
                : generalPoliciesQuery.data
                  ? `General (${generalPoliciesQuery.data.cancellation_min_lead_minutes} min)`
                  : "General";

            return (
              <article key={sport.id} className="rounded-3xl border border-slate-200 bg-white p-4">
                {!isEditing ? (
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <p className="text-lg font-bold text-slate-950">{sport.name}</p>
                      <p className="mt-1 text-sm text-slate-500">{sport.description || "Sin descripción operativa"}</p>
                      <div className="mt-3 flex flex-wrap gap-2 text-xs font-semibold">
                        <span className="rounded-full bg-slate-100 px-3 py-1 text-slate-600">Reserva: {bookingText}</span>
                        <span className="rounded-full bg-slate-100 px-3 py-1 text-slate-600">Cancelación: {cancellationText}</span>
                      </div>
                    </div>

                    <button className="btn-secondary" type="button" onClick={() => startSportEdit(sport.id)}>
                      <PencilLine size={16} />
                      Editar política
                    </button>
                  </div>
                ) : (
                  <form className="grid gap-4" onSubmit={handleUpdateSport}>
                    <textarea
                      className="field min-h-24"
                      value={editSportDescription}
                      onChange={(event) => setEditSportDescription(event.target.value)}
                      placeholder="Descripción breve para el admin o el usuario"
                    />

                    <div className="grid gap-4 sm:grid-cols-2">
                      <div>
                        <label className="mb-2 block text-sm font-semibold text-slate-700" htmlFor={`sport-booking-${sport.id}`}>
                          Ventana de reserva
                        </label>
                        <input
                          id={`sport-booking-${sport.id}`}
                          className="field"
                          type="number"
                          min="0"
                          value={editSportBookingLead}
                          onChange={(event) => setEditSportBookingLead(event.target.value)}
                          placeholder={generalPoliciesQuery.data ? `General: ${generalPoliciesQuery.data.min_booking_lead_minutes}` : "Usar general"}
                        />
                      </div>

                      <div>
                        <label className="mb-2 block text-sm font-semibold text-slate-700" htmlFor={`sport-cancel-${sport.id}`}>
                          Ventana de cancelación
                        </label>
                        <input
                          id={`sport-cancel-${sport.id}`}
                          className="field"
                          type="number"
                          min="0"
                          value={editSportCancellationLead}
                          onChange={(event) => setEditSportCancellationLead(event.target.value)}
                          placeholder={generalPoliciesQuery.data ? `General: ${generalPoliciesQuery.data.cancellation_min_lead_minutes}` : "Usar general"}
                        />
                      </div>
                    </div>

                    <p className="text-xs font-medium text-slate-400">
                      Dejá el campo vacío si querés que este deporte use la política general del complejo.
                    </p>

                    <div className="flex flex-wrap gap-2">
                      <button className="btn-primary" type="submit" disabled={updateSportMutation.isPending}>
                        {updateSportMutation.isPending ? (
                          <span className="inline-flex items-center gap-2">
                            <LoaderCircle className="animate-spin" size={16} />
                            Guardando...
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-2">
                            <Save size={16} />
                            Guardar política
                          </span>
                        )}
                      </button>
                      <button className="btn-secondary" type="button" onClick={() => setEditingSportId(null)}>
                        Cancelar
                      </button>
                    </div>
                  </form>
                )}
              </article>
            );
          })}
        </div>
      ) : (
        <div className="mt-4">
          <EmptyState title="Todavía no hay deportes" description="Cargá al menos un deporte para definir políticas por disciplina." />
        </div>
      )}
    </div>
  );
}

