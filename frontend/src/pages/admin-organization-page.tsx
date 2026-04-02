import { useMutation, useQuery } from "@tanstack/react-query";
import { Building2, CircleAlert, LoaderCircle, Palette, Save, TimerReset } from "lucide-react";
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

  const settingsQuery = useQuery({
    queryKey: ["current-organization-settings"],
    queryFn: api.getCurrentOrganizationSettings,
  });

  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [isActive, setIsActive] = useState(true);
  const [brandingName, setBrandingName] = useState("");
  const [logoUrl, setLogoUrl] = useState("");
  const [primaryColor, setPrimaryColor] = useState("#0f172a");
  const [bookingMinutes, setBookingMinutes] = useState("");
  const [cancellationMinutes, setCancellationMinutes] = useState("");
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

  useEffect(() => {
    if (!settingsQuery.data) {
      return;
    }
    setBrandingName(settingsQuery.data.branding_name ?? "");
    setLogoUrl(settingsQuery.data.logo_url ?? "");
    setPrimaryColor(settingsQuery.data.primary_color ?? "#0f172a");
    setBookingMinutes(settingsQuery.data.booking_min_lead_minutes !== null ? String(settingsQuery.data.booking_min_lead_minutes) : "");
    setCancellationMinutes(
      settingsQuery.data.cancellation_min_lead_minutes !== null ? String(settingsQuery.data.cancellation_min_lead_minutes) : "",
    );
  }, [settingsQuery.data]);

  const updateOrganizationMutation = useMutation({
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

  const updateSettingsMutation = useMutation({
    mutationFn: api.updateCurrentOrganizationSettings,
    onSuccess: () => {
      setError(null);
      setSuccess("Branding y política general actualizados correctamente.");
      void settingsQuery.refetch();
    },
    onError: (mutationError) => {
      setSuccess(null);
      setError(mutationError instanceof Error ? mutationError.message : "No pudimos guardar la configuración.");
    },
  });

  function handleOrganizationSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSuccess(null);

    if (!name.trim() || !slug.trim()) {
      setError("Completá nombre e identificador del complejo.");
      return;
    }

    updateOrganizationMutation.mutate({
      name: name.trim(),
      slug: slug.trim().toLowerCase(),
      is_active: isActive,
    });
  }

  function handleSettingsSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSuccess(null);

    updateSettingsMutation.mutate({
      branding_name: brandingName.trim() || null,
      logo_url: logoUrl.trim() || null,
      primary_color: primaryColor.trim() || null,
      booking_min_lead_minutes: bookingMinutes.trim() ? Number(bookingMinutes) : null,
      cancellation_min_lead_minutes: cancellationMinutes.trim() ? Number(cancellationMinutes) : null,
    });
  }

  if (organizationQuery.isLoading || settingsQuery.isLoading) {
    return (
      <>
        <AppHeader />
        <LoadingCard label="Cargando perfil del complejo..." />
      </>
    );
  }

  return (
    <>
      <AppHeader />
      <section className="space-y-6">
        <AdminNav />

        <SectionTitle
          eyebrow="Admin"
          title="Perfil e identidad del complejo"
          description="Definí cómo se presenta este complejo dentro de la plataforma y ajustá su política general antes de bajar al detalle por deporte."
        />

        <div className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
          <form className="shell-card space-y-5 p-6" onSubmit={handleOrganizationSubmit}>
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-sky-100 text-sky-700">
                <Building2 size={20} />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-950">Configuración general</h3>
                <p className="text-sm text-slate-500">Datos base del tenant y estado operativo del complejo.</p>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <label className="mb-2 block text-sm font-semibold text-slate-700">Nombre comercial</label>
                <input className="field" value={name} onChange={(event) => setName(event.target.value)} />
              </div>

              <div className="sm:col-span-2">
                <label className="mb-2 block text-sm font-semibold text-slate-700">Identificador</label>
                <input className="field" value={slug} onChange={(event) => setSlug(event.target.value)} />
              </div>

              <label className="sm:col-span-2 flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                <input type="checkbox" checked={isActive} onChange={(event) => setIsActive(event.target.checked)} />
                Mantener este complejo activo
              </label>
            </div>

            <button className="btn-primary" type="submit" disabled={updateOrganizationMutation.isPending}>
              {updateOrganizationMutation.isPending ? (
                <span className="inline-flex items-center gap-2">
                  <LoaderCircle className="animate-spin" size={16} />
                  Guardando...
                </span>
              ) : (
                <span className="inline-flex items-center gap-2">
                  <Save size={16} />
                  Guardar perfil
                </span>
              )}
            </button>
          </form>

          <form className="shell-card space-y-5 p-6" onSubmit={handleSettingsSubmit}>
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-violet-100 text-violet-700">
                <Palette size={20} />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-950">Branding y política general</h3>
                <p className="text-sm text-slate-500">Base visual y reglas por defecto para reservas y cancelaciones.</p>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <label className="mb-2 block text-sm font-semibold text-slate-700">Nombre de marca visible</label>
                <input
                  className="field"
                  value={brandingName}
                  onChange={(event) => setBrandingName(event.target.value)}
                  placeholder="Si queda vacío, se usa el nombre comercial"
                />
              </div>

              <div className="sm:col-span-2">
                <label className="mb-2 block text-sm font-semibold text-slate-700">Logo URL</label>
                <input className="field" value={logoUrl} onChange={(event) => setLogoUrl(event.target.value)} placeholder="https://..." />
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-700">Color principal</label>
                <input className="field" value={primaryColor} onChange={(event) => setPrimaryColor(event.target.value)} />
              </div>

              <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                <p className="font-semibold text-slate-900">Vista rápida</p>
                <div className="mt-3 flex items-center gap-3">
                  <span className="h-8 w-8 rounded-full border border-slate-200" style={{ backgroundColor: primaryColor || "#0f172a" }} />
                  <span>{brandingName || name || "Tu complejo"}</span>
                </div>
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-700">Reserva mínima</label>
                <input
                  className="field"
                  type="number"
                  min="0"
                  value={bookingMinutes}
                  onChange={(event) => setBookingMinutes(event.target.value)}
                  placeholder="Ej. 30"
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-700">Cancelación mínima</label>
                <input
                  className="field"
                  type="number"
                  min="0"
                  value={cancellationMinutes}
                  onChange={(event) => setCancellationMinutes(event.target.value)}
                  placeholder="Ej. 120"
                />
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
              <div className="flex items-start gap-2">
                <TimerReset className="mt-0.5 text-skyline" size={16} />
                <div>
                  <p>Estos valores son la política general del complejo.</p>
                  <p className="mt-1">Si un deporte tiene configuración propia, prevalece sobre este default.</p>
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

            {success ? (
              <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                {success}
              </div>
            ) : null}

            <button className="btn-primary" type="submit" disabled={updateSettingsMutation.isPending}>
              {updateSettingsMutation.isPending ? (
                <span className="inline-flex items-center gap-2">
                  <LoaderCircle className="animate-spin" size={16} />
                  Guardando...
                </span>
              ) : (
                <span className="inline-flex items-center gap-2">
                  <Save size={16} />
                  Guardar branding y política
                </span>
              )}
            </button>
          </form>
        </div>
      </section>
    </>
  );
}
