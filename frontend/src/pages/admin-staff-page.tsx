import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CircleAlert, Copy, LoaderCircle, MailCheck, Save, Trash2, Users } from "lucide-react";
import { useState } from "react";
import { AdminNav } from "../components/admin-nav";
import { AppHeader } from "../components/app-header";
import { LoadingCard } from "../components/loading-card";
import { SectionTitle } from "../components/section-title";
import { api } from "../lib/api";
import { confirmDestructiveAction, showTimedSuccess } from "../lib/dialog";

export function AdminStaffPage() {
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState<"admin" | "staff" | "user">("staff");
  const [expiresInDays, setExpiresInDays] = useState("7");
  const [feedback, setFeedback] = useState<string | null>(null);
  const [deliveryInfo, setDeliveryInfo] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const invitationsQuery = useQuery({
    queryKey: ["staff-invitations"],
    queryFn: api.listStaffInvitations,
  });

  const createMutation = useMutation({
    mutationFn: api.createStaffInvitation,
    onSuccess: (result) => {
      setEmail("");
      setFullName("");
      setRole("staff");
      setExpiresInDays("7");
      setError(null);
      setFeedback("Invitación creada correctamente.");
      setDeliveryInfo(result.email_delivery_detail);
      void queryClient.invalidateQueries({ queryKey: ["staff-invitations"] });
    },
    onError: (mutationError) => {
      setFeedback(null);
      setDeliveryInfo(null);
      setError(mutationError instanceof Error ? mutationError.message : "No pudimos crear la invitación.");
    },
  });

  const cancelMutation = useMutation({
    mutationFn: api.cancelStaffInvitation,
    onSuccess: async () => {
      setError(null);
      setDeliveryInfo(null);
      setFeedback(null);
      await showTimedSuccess({
        title: "Invitación cancelada",
        text: "La invitación pendiente se eliminó del listado.",
        timer: 2200,
      });
      void queryClient.invalidateQueries({ queryKey: ["staff-invitations"] });
    },
    onError: (mutationError) => {
      setFeedback(null);
      setDeliveryInfo(null);
      setError(mutationError instanceof Error ? mutationError.message : "No pudimos cancelar la invitación.");
    },
  });

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback(null);
    setDeliveryInfo(null);
    setError(null);

    if (!email.trim()) {
      setError("Completá el email del integrante.");
      return;
    }

    createMutation.mutate({
      email: email.trim(),
      full_name: fullName.trim() || null,
      role,
      expires_in_days: Number(expiresInDays) || 7,
    });
  }

  async function copyInvitation(token: string) {
    const inviteUrl = `${window.location.origin}/accept-invite?token=${token}`;
    try {
      await navigator.clipboard.writeText(inviteUrl);
      setError(null);
      setFeedback("Link de invitación copiado al portapapeles.");
      setDeliveryInfo(null);
    } catch {
      setFeedback(null);
      setDeliveryInfo(null);
      setError("No pudimos copiar el link automáticamente.");
    }
  }

  async function handleCancelInvitation(invitationId: string, emailAddress: string) {
    const confirmed = await confirmDestructiveAction({
      title: "Cancelar invitación",
      text: `Se va a cancelar la invitación pendiente para ${emailAddress}.`,
      confirmText: "Cancelar invitación",
    });

    if (!confirmed) {
      return;
    }

    setFeedback(null);
    setDeliveryInfo(null);
    setError(null);
    cancelMutation.mutate(invitationId);
  }

  return (
    <>
      <AppHeader />
      <section className="space-y-6">
        <AdminNav />

        <SectionTitle
          eyebrow="Admin"
          title="Invitaciones de staff"
          description="Invitá personas al complejo sin compartir tu usuario. El sistema intenta enviar el acceso por email y, si eso no está configurado, deja el link listo para copiar."
        />

        <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
          <form className="shell-card space-y-5 p-6" onSubmit={handleSubmit}>
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-sky-100 text-sky-700">
                <Users size={20} />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-950">Nueva invitación</h3>
                <p className="text-sm text-slate-500">
                  Definí a quién invitás, con qué rol entra y cuántos días tendrá disponible el enlace.
                </p>
              </div>
            </div>

            <div className="grid gap-4">
              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-700">Email</label>
                <input
                  className="field"
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="staff@complejo.com"
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-700">Nombre</label>
                <input
                  className="field"
                  value={fullName}
                  onChange={(event) => setFullName(event.target.value)}
                  placeholder="Nombre opcional"
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-2 block text-sm font-semibold text-slate-700">Rol</label>
                  <select
                    className="field"
                    value={role}
                    onChange={(event) => setRole(event.target.value as "admin" | "staff" | "user")}
                  >
                    <option value="staff">Staff</option>
                    <option value="user">Usuario</option>
                    <option value="admin">Admin</option>
                  </select>
                  <p className="mt-2 text-xs text-slate-500">
                    Staff opera el complejo. Admin además gestiona branding, WhatsApp y usuarios.
                  </p>
                </div>

                <div>
                  <label className="mb-2 block text-sm font-semibold text-slate-700">Vence en</label>
                  <div className="relative">
                    <input
                      className="field pr-16"
                      type="number"
                      min="1"
                      max="90"
                      value={expiresInDays}
                      onChange={(event) => setExpiresInDays(event.target.value)}
                      placeholder="7"
                    />
                    <span className="pointer-events-none absolute inset-y-0 right-4 flex items-center text-sm font-semibold text-slate-400">
                      días
                    </span>
                  </div>
                  <p className="mt-2 text-xs text-slate-500">La invitación dejará de funcionar después de ese plazo.</p>
                </div>
              </div>
            </div>

            {error ? (
              <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                <div className="flex items-start gap-2">
                  <CircleAlert className="mt-0.5" size={16} />
                  <span>{error}</span>
                </div>
              </div>
            ) : null}

            {feedback ? (
              <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                {feedback}
              </div>
            ) : null}

            {deliveryInfo ? (
              <div className="rounded-2xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-800">
                <div className="flex items-start gap-2">
                  <MailCheck className="mt-0.5" size={16} />
                  <span>{deliveryInfo}</span>
                </div>
              </div>
            ) : null}

            <button className="btn-primary" type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? (
                <span className="inline-flex items-center gap-2">
                  <LoaderCircle className="animate-spin" size={16} />
                  Creando...
                </span>
              ) : (
                <span className="inline-flex items-center gap-2">
                  <Save size={16} />
                  Crear invitación
                </span>
              )}
            </button>
          </form>

          <div className="shell-card space-y-4 p-6">
            <h3 className="text-lg font-bold text-slate-950">Invitaciones pendientes</h3>
            {invitationsQuery.isLoading ? (
              <LoadingCard label="Cargando invitaciones..." />
            ) : (invitationsQuery.data ?? []).length === 0 ? (
              <div className="rounded-3xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
                No hay invitaciones pendientes.
              </div>
            ) : (
              <div className="space-y-3">
                {(invitationsQuery.data ?? []).map((invitation) => (
                  <article key={invitation.id} className="rounded-3xl border border-slate-200 bg-white p-4">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                      <div>
                        <p className="text-lg font-bold text-slate-950">{invitation.full_name || invitation.email}</p>
                        <p className="mt-1 text-sm text-slate-500">{invitation.email}</p>
                        <div className="mt-2 flex flex-wrap gap-2 text-xs font-semibold">
                          <span className="rounded-full bg-slate-100 px-3 py-1 text-slate-600">
                            {invitation.role === "admin"
                              ? "Admin"
                              : invitation.role === "staff"
                                ? "Staff"
                                : "Usuario"}
                          </span>
                          <span className="rounded-full bg-slate-100 px-3 py-1 text-slate-600">
                            Pendiente
                          </span>
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <button className="btn-secondary" type="button" onClick={() => copyInvitation(invitation.invite_token)}>
                          <Copy size={16} />
                          Copiar link
                        </button>
                        <button
                          className="btn-secondary"
                          type="button"
                          onClick={() => handleCancelInvitation(invitation.id, invitation.email)}
                          disabled={cancelMutation.isPending}
                        >
                          <Trash2 size={16} />
                          Cancelar
                        </button>
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </div>
        </div>
      </section>
    </>
  );
}
