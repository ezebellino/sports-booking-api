import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Building2,
  CircleAlert,
  ImageUp,
  LoaderCircle,
  Palette,
  PlusCircle,
  Save,
  TimerReset,
} from "lucide-react";
import { useEffect, useMemo, useState, type ChangeEvent } from "react";
import { AdminNav } from "../components/admin-nav";
import { AppHeader } from "../components/app-header";
import { LoadingCard } from "../components/loading-card";
import { SectionTitle } from "../components/section-title";
import { api } from "../lib/api";
import { useSessionTour } from "../lib/session-tour";

type SportFormState = {
  name: string;
  description: string;
  bookingMinutes: string;
  cancellationMinutes: string;
};

const emptySportForm: SportFormState = {
  name: "",
  description: "",
  bookingMinutes: "",
  cancellationMinutes: "",
};

export function AdminOrganizationPage() {
  const queryClient = useQueryClient();
  const organizationQuery = useQuery({
    queryKey: ["current-organization"],
    queryFn: api.getCurrentOrganization,
  });

  const settingsQuery = useQuery({
    queryKey: ["current-organization-settings"],
    queryFn: api.getCurrentOrganizationSettings,
  });

  const organizationSportsQuery = useQuery({
    queryKey: ["current-organization-sports"],
    queryFn: api.listCurrentOrganizationSports,
  });

  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [isActive, setIsActive] = useState(true);
  const [brandingName, setBrandingName] = useState("");
  const [logoUrl, setLogoUrl] = useState("");
  const [primaryColor, setPrimaryColor] = useState("#0f172a");
  const [bookingMinutes, setBookingMinutes] = useState("");
  const [cancellationMinutes, setCancellationMinutes] = useState("");
  const [enabledSportIds, setEnabledSportIds] = useState<string[]>([]);
  const [sportForm, setSportForm] = useState<SportFormState>(emptySportForm);
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [logoPreviewUrl, setLogoPreviewUrl] = useState<string | null>(null);
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
    setBookingMinutes(
      settingsQuery.data.booking_min_lead_minutes !== null
        ? String(settingsQuery.data.booking_min_lead_minutes)
        : "",
    );
    setCancellationMinutes(
      settingsQuery.data.cancellation_min_lead_minutes !== null
        ? String(settingsQuery.data.cancellation_min_lead_minutes)
        : "",
    );
  }, [settingsQuery.data]);

  useEffect(() => {
    return () => {
      if (logoPreviewUrl) {
        URL.revokeObjectURL(logoPreviewUrl);
      }
    };
  }, [logoPreviewUrl]);

  useEffect(() => {
    if (!organizationSportsQuery.data) {
      return;
    }
    setEnabledSportIds(
      organizationSportsQuery.data.filter((item) => item.is_enabled).map((item) => item.sport.id),
    );
  }, [organizationSportsQuery.data]);

  useSessionTour({
    sessionKey: "tour:admin-organization",
    enabled:
      !organizationQuery.isLoading &&
      !settingsQuery.isLoading &&
      !organizationSportsQuery.isLoading,
    steps: [
      {
        element: '[data-tour="admin-nav"]',
        popover: {
          title: "Módulos del admin",
          description: "Desde acá navegás entre la operación del complejo sin salir del panel.",
        },
      },
      {
        element: '[data-tour="org-profile"]',
        popover: {
          title: "Perfil del complejo",
          description: "Definí nombre, slug y estado operativo del tenant.",
        },
      },
      {
        element: '[data-tour="org-settings"]',
        popover: {
          title: "Branding y política general",
          description: "Acá configurás identidad visual y reglas base de reserva/cancelación.",
        },
      },
      {
        element: '[data-tour="org-sports"]',
        popover: {
          title: "Deportes habilitados",
          description: "El catálogo es global, pero cada complejo decide cuáles mostrar y operar.",
        },
      },
      {
        element: '[data-tour="org-create-sport"]',
        popover: {
          title: "Crear deporte",
          description: "Si falta una disciplina, la podés dar de alta desde acá como admin.",
        },
      },
    ],
  });

  const enabledSportsCount = useMemo(() => enabledSportIds.length, [enabledSportIds]);

  const updateOrganizationMutation = useMutation({
    mutationFn: api.updateCurrentOrganization,
    onSuccess: (organization) => {
      setName(organization.name);
      setSlug(organization.slug);
      setIsActive(organization.is_active);
      setError(null);
      setSuccess("Perfil del complejo actualizado correctamente.");
      void organizationQuery.refetch();
      void queryClient.invalidateQueries({ queryKey: ["request-organization-context"] });
      void queryClient.invalidateQueries({ queryKey: ["current-organization"] });
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
      void queryClient.invalidateQueries({ queryKey: ["request-organization-context"] });
      void queryClient.invalidateQueries({ queryKey: ["current-organization-settings"] });
    },
    onError: (mutationError) => {
      setSuccess(null);
      setError(
        mutationError instanceof Error ? mutationError.message : "No pudimos guardar la configuración.",
      );
    },
  });

  const updateSportsMutation = useMutation({
    mutationFn: api.updateCurrentOrganizationSports,
    onSuccess: (sports) => {
      setEnabledSportIds(sports.filter((item) => item.is_enabled).map((item) => item.sport.id));
      setError(null);
      setSuccess("Deportes habilitados actualizados correctamente.");
      void organizationSportsQuery.refetch();
      void queryClient.invalidateQueries({ queryKey: ["sports"] });
      void queryClient.invalidateQueries({ queryKey: ["venues"] });
      void queryClient.invalidateQueries({ queryKey: ["courts"] });
      void queryClient.invalidateQueries({ queryKey: ["timeslots"] });
    },
    onError: (mutationError) => {
      setSuccess(null);
      setError(
        mutationError instanceof Error
          ? mutationError.message
          : "No pudimos actualizar los deportes habilitados.",
      );
    },
  });

  const createSportMutation = useMutation({
    mutationFn: api.createSport,
    onSuccess: () => {
      setSportForm(emptySportForm);
      setError(null);
      setSuccess("Deporte creado y habilitado para este complejo.");
      void queryClient.invalidateQueries({ queryKey: ["current-organization-sports"] });
      void queryClient.invalidateQueries({ queryKey: ["sports"] });
      void queryClient.invalidateQueries({ queryKey: ["venues"] });
      void queryClient.invalidateQueries({ queryKey: ["courts"] });
      void queryClient.invalidateQueries({ queryKey: ["timeslots"] });
    },
    onError: (mutationError) => {
      setSuccess(null);
      setError(mutationError instanceof Error ? mutationError.message : "No pudimos crear el deporte.");
    },
  });

  const uploadLogoMutation = useMutation({
    mutationFn: api.uploadCurrentOrganizationLogo,
    onSuccess: (settings) => {
      if (logoPreviewUrl) {
        URL.revokeObjectURL(logoPreviewUrl);
      }
      setLogoFile(null);
      setLogoPreviewUrl(null);
      setLogoUrl(settings.logo_url ?? "");
      setError(null);
      setSuccess("Logo actualizado correctamente.");
      void queryClient.invalidateQueries({ queryKey: ["current-organization-settings"] });
      void queryClient.invalidateQueries({ queryKey: ["request-organization-context"] });
    },
    onError: (mutationError) => {
      setSuccess(null);
      setError(mutationError instanceof Error ? mutationError.message : "No pudimos subir el logo.");
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
      cancellation_min_lead_minutes: cancellationMinutes.trim()
        ? Number(cancellationMinutes)
        : null,
    });
  }

  function handleSportsSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSuccess(null);
    updateSportsMutation.mutate(enabledSportIds);
  }

  function handleCreateSportSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSuccess(null);

    if (!sportForm.name.trim()) {
      setError("Completá al menos el nombre del deporte.");
      return;
    }

    createSportMutation.mutate({
      name: sportForm.name.trim(),
      description: sportForm.description.trim() || null,
      booking_min_lead_minutes: sportForm.bookingMinutes.trim()
        ? Number(sportForm.bookingMinutes)
        : null,
      cancellation_min_lead_minutes: sportForm.cancellationMinutes.trim()
        ? Number(sportForm.cancellationMinutes)
        : null,
    });
  }

  function toggleSport(sportId: string) {
    setEnabledSportIds((current) =>
      current.includes(sportId) ? current.filter((item) => item !== sportId) : [...current, sportId],
    );
  }

  function updateSportForm<K extends keyof SportFormState>(key: K, value: SportFormState[K]) {
    setSportForm((current) => ({ ...current, [key]: value }));
  }

  function handleLogoSelected(event: ChangeEvent<HTMLInputElement>) {
    const nextFile = event.target.files?.[0] ?? null;
    if (logoPreviewUrl) {
      URL.revokeObjectURL(logoPreviewUrl);
    }

    if (!nextFile) {
      setLogoFile(null);
      setLogoPreviewUrl(null);
      return;
    }

    setLogoFile(nextFile);
    setLogoPreviewUrl(URL.createObjectURL(nextFile));
    setError(null);
    setSuccess(null);
  }

  function handleLogoUpload() {
    if (!logoFile) {
      setError("Seleccioná un archivo antes de subir el logo.");
      setSuccess(null);
      return;
    }

    setError(null);
    setSuccess(null);
    uploadLogoMutation.mutate(logoFile);
  }

  const effectiveLogoPreview = logoPreviewUrl || logoUrl || null;

  if (organizationQuery.isLoading || settingsQuery.isLoading || organizationSportsQuery.isLoading) {
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
          description="Definí cómo se presenta este complejo dentro de la plataforma, qué deportes ofrece y cuál es su política general antes de bajar al detalle por disciplina."
        />

        <div className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
          <form className="shell-card space-y-5 p-6" onSubmit={handleOrganizationSubmit} data-tour="org-profile">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-sky-100 text-sky-700">
                <Building2 size={20} />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-950">Configuración general</h3>
                <p className="text-sm text-slate-500">
                  Datos base del tenant y estado operativo del complejo.
                </p>
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
                <input
                  type="checkbox"
                  checked={isActive}
                  onChange={(event) => setIsActive(event.target.checked)}
                />
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

          <form className="shell-card space-y-5 p-6" onSubmit={handleSettingsSubmit} data-tour="org-settings">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-violet-100 text-violet-700">
                <Palette size={20} />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-950">Branding y política general</h3>
                <p className="text-sm text-slate-500">
                  Base visual y reglas por defecto para reservas y cancelaciones.
                </p>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="sm:col-span-2 rounded-2xl border border-slate-200 bg-slate-50 p-4" data-tour="org-logo-upload">
                <div className="flex items-start gap-3">
                  <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-900 text-white">
                    <ImageUp size={18} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold text-slate-900">Logo del complejo</p>
                    <p className="mt-1 text-sm text-slate-500">
                      La forma recomendada es subir un archivo. El campo URL queda disponible como opción avanzada.
                    </p>
                  </div>
                </div>

                <div className="mt-4 flex flex-col gap-4 lg:flex-row lg:items-center">
                  <div className="flex h-24 w-24 items-center justify-center overflow-hidden rounded-3xl border border-slate-200 bg-white">
                    {effectiveLogoPreview ? (
                      <img
                        src={effectiveLogoPreview}
                        alt="Preview del logo del complejo"
                        className="h-full w-full object-contain"
                      />
                    ) : (
                      <span className="px-3 text-center text-xs font-semibold text-slate-400">Sin logo</span>
                    )}
                  </div>

                  <div className="flex-1 space-y-3">
                    <input
                      type="file"
                      accept="image/png,image/jpeg,image/webp,image/svg+xml"
                      onChange={handleLogoSelected}
                      className="block w-full text-sm text-slate-600 file:mr-4 file:rounded-2xl file:border-0 file:bg-slate-900 file:px-4 file:py-3 file:text-sm file:font-semibold file:text-white"
                    />
                    <p className="text-xs text-slate-500">
                      Formatos permitidos: PNG, JPG, WEBP o SVG. Tamaño máximo: 2 MB.
                    </p>
                    <div className="flex flex-wrap gap-3">
                      <button
                        className="btn-secondary"
                        type="button"
                        disabled={!logoFile || uploadLogoMutation.isPending}
                        onClick={handleLogoUpload}
                      >
                        {uploadLogoMutation.isPending ? (
                          <span className="inline-flex items-center gap-2">
                            <LoaderCircle className="animate-spin" size={16} />
                            Subiendo...
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-2">
                            <ImageUp size={16} />
                            Subir logo
                          </span>
                        )}
                      </button>
                      {logoFile ? (
                        <span className="self-center text-xs text-slate-500">
                          Archivo listo: {logoFile.name}
                        </span>
                      ) : null}
                    </div>
                  </div>
                </div>
              </div>

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
                <input
                  className="field"
                  value={logoUrl}
                  onChange={(event) => setLogoUrl(event.target.value)}
                  placeholder="https://..."
                />
                <p className="mt-2 text-xs text-slate-500">
                  Usalo solo si preferís cargar una imagen remota manualmente.
                </p>
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-700">Color principal</label>
                <input
                  className="field"
                  value={primaryColor}
                  onChange={(event) => setPrimaryColor(event.target.value)}
                />
              </div>

              <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                <p className="font-semibold text-slate-900">Vista rápida</p>
                <div className="mt-3 flex items-center gap-3">
                  <span
                    className="h-8 w-8 rounded-full border border-slate-200"
                    style={{ backgroundColor: primaryColor || "#0f172a" }}
                  />
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

        <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
          <form className="shell-card space-y-5 p-6" onSubmit={handleSportsSubmit} data-tour="org-sports">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-amber-100 text-amber-700">
                <TimerReset size={20} />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-950">Deportes habilitados</h3>
                <p className="text-sm text-slate-500">
                  El catálogo es global, pero cada complejo decide cuáles ofrece y cuáles deja ocultos.
                </p>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
              <p>
                Hay <span className="font-semibold text-slate-900">{enabledSportsCount}</span> deportes habilitados
                sobre{" "}
                <span className="font-semibold text-slate-900">
                  {organizationSportsQuery.data?.length ?? 0}
                </span>{" "}
                disponibles en catálogo.
              </p>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              {(organizationSportsQuery.data ?? []).map((item) => (
                <label
                  key={item.sport.id}
                  className={`flex cursor-pointer items-start gap-3 rounded-2xl border px-4 py-3 text-sm ${
                    enabledSportIds.includes(item.sport.id)
                      ? "border-sky-300 bg-sky-50"
                      : "border-slate-200 bg-white"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={enabledSportIds.includes(item.sport.id)}
                    onChange={() => toggleSport(item.sport.id)}
                    className="mt-1"
                  />
                  <div>
                    <p className="font-semibold text-slate-900">{item.sport.name}</p>
                    <p className="mt-1 text-slate-500">{item.sport.description || "Sin descripción operativa"}</p>
                  </div>
                </label>
              ))}
            </div>

            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
              <p>
                Cuando un deporte se deshabilita, deja de aparecer en explorar, inventario operativo y filtros de turnos para este complejo.
              </p>
            </div>

            <button className="btn-primary" type="submit" disabled={updateSportsMutation.isPending}>
              {updateSportsMutation.isPending ? (
                <span className="inline-flex items-center gap-2">
                  <LoaderCircle className="animate-spin" size={16} />
                  Guardando...
                </span>
              ) : (
                <span className="inline-flex items-center gap-2">
                  <Save size={16} />
                  Guardar deportes habilitados
                </span>
              )}
            </button>
          </form>

          <form className="shell-card space-y-5 p-6" onSubmit={handleCreateSportSubmit} data-tour="org-create-sport">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-700">
                <PlusCircle size={20} />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-950">Crear deporte</h3>
                <p className="text-sm text-slate-500">
                  Alta de un deporte nuevo en el catálogo global. Queda habilitado automáticamente para este complejo.
                </p>
              </div>
            </div>

            <div className="grid gap-4">
              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-700">Nombre</label>
                <input
                  className="field"
                  value={sportForm.name}
                  onChange={(event) => updateSportForm("name", event.target.value)}
                  placeholder="Ej. Pádel"
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-700">Descripción</label>
                <textarea
                  className="field min-h-28 resize-y"
                  value={sportForm.description}
                  onChange={(event) => updateSportForm("description", event.target.value)}
                  placeholder="Texto corto para admins y usuarios."
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-2 block text-sm font-semibold text-slate-700">Reserva mínima</label>
                  <input
                    className="field"
                    type="number"
                    min="0"
                    value={sportForm.bookingMinutes}
                    onChange={(event) => updateSportForm("bookingMinutes", event.target.value)}
                    placeholder="Opcional"
                  />
                </div>

                <div>
                  <label className="mb-2 block text-sm font-semibold text-slate-700">Cancelación mínima</label>
                  <input
                    className="field"
                    type="number"
                    min="0"
                    value={sportForm.cancellationMinutes}
                    onChange={(event) => updateSportForm("cancellationMinutes", event.target.value)}
                    placeholder="Opcional"
                  />
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
              <p>
                Este alta impacta en el catálogo global. Después podés habilitarlo o deshabilitarlo por complejo desde este mismo panel.
              </p>
            </div>

            <button className="btn-primary" type="submit" disabled={createSportMutation.isPending}>
              {createSportMutation.isPending ? (
                <span className="inline-flex items-center gap-2">
                  <LoaderCircle className="animate-spin" size={16} />
                  Creando...
                </span>
              ) : (
                <span className="inline-flex items-center gap-2">
                  <PlusCircle size={16} />
                  Crear deporte
                </span>
              )}
            </button>
          </form>
        </div>
      </section>
    </>
  );
}
