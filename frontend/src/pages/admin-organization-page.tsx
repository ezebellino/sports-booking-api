import { useMutation, useQuery } from "@tanstack/react-query";
import { Building2, CircleAlert, LoaderCircle, Save } from "lucide-react";
import { useEffect, useState } from "react";
import { AdminNav } from "../components/admin-nav";
import { AppHeader } from "../components/app-header";
import { LoadingCard } from "../components/loading-card";
import { SectionTitle } from "../components/section-title";
import { api } from "../lib/api";

export function AdminOrganizationPage() {
  const organizationQuery = useQuery({
    queryKey: ["current-organization"],
    queryFn: api.getCurrentOrganization,
  });

  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [isActive, setIsActive] = useState(true);
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!organizationQuery.data) {
      return;
    }
    setName(organizationQuery.data.name);
    setSlug(organizationQuery.data.slug);
    setIsActive(organizationQuery.data.is_active);
  }, [organizationQuery.data]);

  const updateMutation = useMutation({
    mutationFn: api.updateCurrentOrganization,
    onSuccess: (organization) => {
      setName(organization.name);
      setSlug(organization.slug);
      setIsActive(organization.is_active);
      setError(null);
      setSuccess("Perfil del complejo actualizado correctamente.");
      void organizationQuery.refetch();
    },
    onError: (mutationError) => {
      setSuccess(null);
      setError(mutationError instanceof Error ? mutationError.message : "No pudimos guardar el complejo.");
    },
  });

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSuccess(null);

    if (!name.trim() || !slug.trim()) {
      setError("Completá nombre e identificador del complejo.");
      return;
    }

    updateMutation.mutate({
      name: name.trim(),
      slug: slug.trim().toLowerCase(),
      is_active: isActive,
    });
  }

  return (
    <>
      <AppHeader />
      <section className="space-y-6">
        <AdminNav />

        <SectionTitle
          eyebrow="Admin"
          title="Perfil del complejo"
          description="Definí cómo se presenta este complejo dentro de la plataforma y mantené ordenado el identificador que usa el tenant."
        />

        {organizationQuery.isLoading ? (
          <LoadingCard label="Cargando perfil del complejo..." />
        ) : (
          <form className="shell-card mx-auto max-w-3xl space-y-5 p-6" onSubmit={handleSubmit}>
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-sky-100 text-sky-700">
                <Building2 size={20} />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-950">Configuración general</h3>
                <p className="text-sm text-slate-500">Estos datos identifican al complejo dentro del SaaS.</p>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <label className="mb-2 block text-sm font-semibold text-slate-700" htmlFor="organization-name">
                  Nombre comercial
                </label>
                <input
                  id="organization-name"
                  className="field"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  placeholder="Ej. Complejo Norte"
                />
              </div>

              <div className="sm:col-span-2">
                <label className="mb-2 block text-sm font-semibold text-slate-700" htmlFor="organization-slug">
                  Identificador
                </label>
                <input
                  id="organization-slug"
                  className="field"
                  value={slug}
                  onChange={(event) => setSlug(event.target.value)}
                  placeholder="ej-complejo-norte"
                />
                <p className="mt-2 text-xs text-slate-500">Usalo como referencia interna y para futuras URLs de tenant.</p>
              </div>

              <label className="sm:col-span-2 flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                <input type="checkbox" checked={isActive} onChange={(event) => setIsActive(event.target.checked)} />
                Mantener este complejo activo
              </label>
            </div>

            {error ? (
              <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                <div className="flex items-start gap-2">
                  <CircleAlert className="mt-0.5" size={16} />
                  <span>{error}</span>
                </div>
              </div>
            ) : null}

            {success ? (
              <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                {success}
              </div>
            ) : null}

            <button className="btn-primary" type="submit" disabled={updateMutation.isPending || organizationQuery.isLoading}>
              {updateMutation.isPending ? (
                <span className="inline-flex items-center gap-2">
                  <LoaderCircle className="animate-spin" size={16} />
                  Guardando...
                </span>
              ) : (
                <span className="inline-flex items-center gap-2">
                  <Save size={16} />
                  Guardar perfil del complejo
                </span>
              )}
            </button>
          </form>
        )}
      </section>
    </>
  );
}
