import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CircleAlert, Copy, LoaderCircle, Save, Users } from "lucide-react";
import { useState } from "react";
import { AdminNav } from "../components/admin-nav";
import { AppHeader } from "../components/app-header";
import { LoadingCard } from "../components/loading-card";
import { SectionTitle } from "../components/section-title";
import { api } from "../lib/api";

export function AdminStaffPage() {
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState<"admin" | "user">("user");
  const [expiresInDays, setExpiresInDays] = useState("7");
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const invitationsQuery = useQuery({
    queryKey: ["staff-invitations"],
    queryFn: api.listStaffInvitations,
  });

  const createMutation = useMutation({
    mutationFn: api.createStaffInvitation,
    onSuccess: () => {
      setEmail("");
      setFullName("");
      setRole("user");
      setExpiresInDays("7");
      setError(null);
      setFeedback("Invitación creada correctamente.");
      void queryClient.invalidateQueries({ queryKey: ["staff-invitations"] });
    },
    onError: (mutationError) => {
      setFeedback(null);
      setError(mutationError instanceof Error ? mutationError.message : "No pudimos crear la invitación.");
    },
  });

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback(null);
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
    } catch {
      setFeedback(null);
      setError("No pudimos copiar el link automáticamente.");
    }
  }

  return (
    <>
      <AppHeader />
      <section className="space-y-6">
        <AdminNav />

        <SectionTitle
          eyebrow="Admin"
          title="Invitaciones de staff"
          description="Invitá personas al complejo sin compartir tu usuario. Cada link crea una cuenta nueva dentro del tenant actual."
        />

        <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
          <form className="shell-card space-y-4 p-6" onSubmit={handleSubmit}>
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-sky-100 text-sky-700">
                <Users size={20} />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-950">Nueva invitación</h3>
                <p className="text-sm text-slate-500">Elegí si la persona entra como admin o usuario del complejo.</p>
              </div>
            </div>

            <input
              className="field"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="staff@complejo.com"
            />
            <input
              className="field"
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
              placeholder="Nombre opcional"
            />
            <div className="grid gap-4 sm:grid-cols-2">
              <select className="field" value={role} onChange={(event) => setRole(event.target.value as "admin" | "user")}>
                <option value="user">Usuario</option>
                <option value="admin">Admin</option>
              </select>
              <input
                className="field"
                type="number"
                min="1"
                max="90"
                value={expiresInDays}
                onChange={(event) => setExpiresInDays(event.target.value)}
                placeholder="7"
              />
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
            <h3 className="text-lg font-bold text-slate-950">Invitaciones emitidas</h3>
            {invitationsQuery.isLoading ? (
              <LoadingCard label="Cargando invitaciones..." />
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
                            {invitation.role === "admin" ? "Admin" : "Usuario"}
                          </span>
                          <span className="rounded-full bg-slate-100 px-3 py-1 text-slate-600">{invitation.status}</span>
                        </div>
                      </div>
                      <button className="btn-secondary" type="button" onClick={() => copyInvitation(invitation.invite_token)}>
                        <Copy size={16} />
                        Copiar link
                      </button>
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
