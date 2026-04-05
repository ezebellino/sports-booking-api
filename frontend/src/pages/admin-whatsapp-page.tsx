import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BellRing,
  CheckCircle2,
  LoaderCircle,
  MessageCircleMore,
  Save,
  Smartphone,
  Wrench,
} from "lucide-react";
import { useEffect, useState } from "react";
import { AppHeader } from "../components/app-header";
import { AdminNav } from "../components/admin-nav";
import { LoadingCard } from "../components/loading-card";
import { SectionTitle } from "../components/section-title";
import { api } from "../lib/api";

function StatusPill({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${
        ok ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"
      }`}
    >
      {label}
    </span>
  );
}

export function AdminWhatsappPage() {
  const queryClient = useQueryClient();
  const notificationStatusQuery = useQuery({
    queryKey: ["admin-whatsapp-status"],
    queryFn: api.getNotificationStatus,
  });

  const settingsQuery = useQuery({
    queryKey: ["current-organization-settings"],
    queryFn: api.getCurrentOrganizationSettings,
  });

  const [provider, setProvider] = useState("");
  const [accessToken, setAccessToken] = useState("");
  const [phoneNumberId, setPhoneNumberId] = useState("");
  const [templateLanguage, setTemplateLanguage] = useState("es_AR");
  const [bookingConfirmedTemplate, setBookingConfirmedTemplate] = useState("");
  const [bookingCancelledTemplate, setBookingCancelledTemplate] = useState("");
  const [recipientOverride, setRecipientOverride] = useState("");
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!settingsQuery.data) {
      return;
    }
    setProvider(settingsQuery.data.whatsapp_provider ?? "");
    setAccessToken("");
    setPhoneNumberId(settingsQuery.data.whatsapp_phone_number_id ?? "");
    setTemplateLanguage(settingsQuery.data.whatsapp_template_language ?? "es_AR");
    setBookingConfirmedTemplate(settingsQuery.data.whatsapp_template_booking_confirmed ?? "");
    setBookingCancelledTemplate(settingsQuery.data.whatsapp_template_booking_cancelled ?? "");
    setRecipientOverride(settingsQuery.data.whatsapp_recipient_override ?? "");
  }, [settingsQuery.data]);

  const updateSettingsMutation = useMutation({
    mutationFn: api.updateCurrentOrganizationSettings,
    onSuccess: () => {
      setError(null);
      setSuccess("Configuración de WhatsApp actualizada correctamente.");
      void queryClient.invalidateQueries({ queryKey: ["current-organization-settings"] });
      void queryClient.invalidateQueries({ queryKey: ["admin-whatsapp-status"] });
    },
    onError: (mutationError) => {
      setSuccess(null);
      setError(mutationError instanceof Error ? mutationError.message : "No pudimos guardar la configuración de WhatsApp.");
    },
  });

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSuccess(null);

    updateSettingsMutation.mutate({
      whatsapp_provider: provider.trim() || null,
      whatsapp_access_token: accessToken.trim() || undefined,
      whatsapp_phone_number_id: phoneNumberId.trim() || null,
      whatsapp_template_language: templateLanguage.trim() || null,
      whatsapp_template_booking_confirmed: bookingConfirmedTemplate.trim() || null,
      whatsapp_template_booking_cancelled: bookingCancelledTemplate.trim() || null,
      whatsapp_recipient_override: recipientOverride.trim() || null,
    });
  }

  if (notificationStatusQuery.isLoading || settingsQuery.isLoading) {
    return (
      <>
        <AppHeader />
        <LoadingCard label="Revisando la configuración de WhatsApp..." />
      </>
    );
  }

  const status = notificationStatusQuery.data;
  if (!status) {
    return (
      <>
        <AppHeader />
        <LoadingCard label="No pudimos cargar el estado de WhatsApp." />
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
          title="Operación de WhatsApp"
          description="Controlá si la integración de este complejo está lista para producción, qué templates usa el sistema y qué falta completar antes de enviar mensajes reales a los clientes."
        />

        <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
          <div className="space-y-4">
            <div className="shell-card space-y-5 p-5">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-700">
                  <MessageCircleMore size={20} />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-slate-950">Estado operativo</h3>
                  <p className="text-sm text-slate-500">Resumen rápido para saber si el canal está en modo prueba o listo para producción.</p>
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-3">
                <div className="rounded-3xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Proveedor</p>
                  <p className="mt-2 text-lg font-bold text-slate-950">{status.provider === "meta_cloud" ? "Meta Cloud" : "Deshabilitado"}</p>
                  <p className="mt-2 text-sm text-slate-500">{status.enabled ? "Canal habilitado para WhatsApp real." : "Todavía no se activó el proveedor real."}</p>
                </div>

                <div className="rounded-3xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Modo actual</p>
                  <p className="mt-2 text-lg font-bold text-slate-950">{status.test_mode ? "Pruebas" : "Producción"}</p>
                  <p className="mt-2 text-sm text-slate-500">
                    {status.test_mode
                      ? "Hay un número override activo, así que los envíos van a ese destino de prueba."
                      : "Los mensajes salen al número real que tenga cargado cada usuario."}
                  </p>
                </div>

                <div className="rounded-3xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Listo para enviar</p>
                  <p className="mt-2 text-lg font-bold text-slate-950">{status.ready_for_live_send ? "Sí" : "Todavía no"}</p>
                  <p className="mt-2 text-sm text-slate-500">
                    {status.ready_for_live_send
                      ? "Las credenciales y los templates mínimos ya están definidos."
                      : "Falta completar al menos un punto obligatorio del checklist."}
                  </p>
                </div>
              </div>

              <div className="rounded-3xl border border-slate-200 bg-white p-4">
                <div className="flex items-center gap-3">
                  <BellRing className="text-skyline" size={18} />
                  <div>
                    <p className="font-semibold text-slate-950">Checklist de activación</p>
                    <p className="text-sm text-slate-500">Cada punto te dice si ya está cubierto y qué revisar si no lo está.</p>
                  </div>
                </div>

                <div className="mt-4 space-y-3">
                  {status.checks.map((check) => (
                    <div key={check.key} className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                        <div>
                          <p className="font-semibold text-slate-900">{check.label}</p>
                          <p className="mt-1 text-sm text-slate-500">{check.ok ? "Configurado correctamente." : check.detail}</p>
                        </div>
                        <StatusPill ok={check.ok} label={check.ok ? "OK" : check.severity === "optional" ? "Opcional" : "Pendiente"} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <form className="shell-card space-y-4 p-5" onSubmit={handleSubmit}>
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-sky-100 text-sky-700">
                  <Save size={20} />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-slate-950">Configuración tenant-level</h3>
                  <p className="text-sm text-slate-500">Estas credenciales y templates aplican solo a este complejo.</p>
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-2 block text-sm font-semibold text-slate-700">Proveedor</label>
                  <select className="field" value={provider} onChange={(event) => setProvider(event.target.value)}>
                    <option value="">Deshabilitado</option>
                    <option value="meta_cloud">Meta Cloud</option>
                  </select>
                </div>

                <div>
                  <label className="mb-2 block text-sm font-semibold text-slate-700">Idioma del template</label>
                  <input className="field" value={templateLanguage} onChange={(event) => setTemplateLanguage(event.target.value)} placeholder="es_AR" />
                </div>

                <div className="sm:col-span-2">
                  <label className="mb-2 block text-sm font-semibold text-slate-700">Access token</label>
                  <input
                    className="field"
                    value={accessToken}
                    onChange={(event) => setAccessToken(event.target.value)}
                    placeholder={settingsQuery.data?.has_whatsapp_access_token ? "Dejá vacío para conservar el token actual" : "Pegar token"}
                  />
                </div>

                <div className="sm:col-span-2">
                  <label className="mb-2 block text-sm font-semibold text-slate-700">Phone number ID</label>
                  <input className="field" value={phoneNumberId} onChange={(event) => setPhoneNumberId(event.target.value)} />
                </div>

                <div className="sm:col-span-2">
                  <label className="mb-2 block text-sm font-semibold text-slate-700">Template de confirmación</label>
                  <input className="field" value={bookingConfirmedTemplate} onChange={(event) => setBookingConfirmedTemplate(event.target.value)} />
                </div>

                <div className="sm:col-span-2">
                  <label className="mb-2 block text-sm font-semibold text-slate-700">Template de cancelación</label>
                  <input className="field" value={bookingCancelledTemplate} onChange={(event) => setBookingCancelledTemplate(event.target.value)} />
                </div>

                <div className="sm:col-span-2">
                  <label className="mb-2 block text-sm font-semibold text-slate-700">Número override para pruebas</label>
                  <input className="field" value={recipientOverride} onChange={(event) => setRecipientOverride(event.target.value)} placeholder="5491122334455" />
                </div>
              </div>

              {error ? <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div> : null}

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
                    Guardar configuración
                  </span>
                )}
              </button>
            </form>
          </div>

          <div className="space-y-4">
            <div className="shell-card p-5">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-amber-100 text-amber-700">
                  <Smartphone size={20} />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-slate-950">Templates activos</h3>
                  <p className="text-sm text-slate-500">Nombres que usa el sistema cuando confirma o cancela una reserva.</p>
                </div>
              </div>

              <div className="mt-4 space-y-3 text-sm text-slate-600">
                <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                  <p className="font-semibold text-slate-900">Confirmación de reserva</p>
                  <p className="mt-1 break-all font-mono text-xs text-slate-500">{status.booking_confirmed_template || "Sin definir"}</p>
                  <div className="mt-2">
                    <StatusPill ok={status.has_booking_confirmed_template} label={status.has_booking_confirmed_template ? "Template listo" : "Falta definir"} />
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                  <p className="font-semibold text-slate-900">Cancelación de reserva</p>
                  <p className="mt-1 break-all font-mono text-xs text-slate-500">{status.booking_cancelled_template || "Sin definir"}</p>
                  <div className="mt-2">
                    <StatusPill ok={status.has_booking_cancelled_template} label={status.has_booking_cancelled_template ? "Template listo" : "Falta definir"} />
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                  <p className="font-semibold text-slate-900">Idioma de template</p>
                  <p className="mt-1 font-mono text-xs text-slate-500">{status.template_language}</p>
                </div>
              </div>
            </div>

            <div className="shell-card p-5">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-100 text-slate-700">
                  <Wrench size={20} />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-slate-950">Qué revisar antes de salir en vivo</h3>
                  <p className="text-sm text-slate-500">Checklist corto para evitar pruebas sobre clientes reales.</p>
                </div>
              </div>

              {status.missing_items.length ? (
                <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                  <p className="font-semibold">Todavía falta completar:</p>
                  <ul className="mt-2 list-disc space-y-1 pl-5">
                    {status.missing_items.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              ) : (
                <div className="mt-4 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
                  <div className="flex items-start gap-2">
                    <CheckCircle2 className="mt-0.5" size={16} />
                    <p>La integración ya tiene cubiertos todos los requisitos mínimos para operar.</p>
                  </div>
                </div>
              )}

              <div className="mt-4 space-y-3 text-sm text-slate-600">
                <p>
                  {status.test_mode
                    ? "Mientras el override siga activo, todos los envíos irán al número de prueba. Es ideal para validar templates sin tocar clientes reales."
                    : "Sin override, el sistema usará el número de WhatsApp que tenga guardado cada usuario con opt-in activo."}
                </p>
                <p>
                  Número override actual: <span className="font-semibold text-slate-900">{status.recipient_override || "No configurado"}</span>
                </p>
                <p>Recomendación: hacé una reserva de prueba y una cancelación de prueba después de cada cambio de template o credencial.</p>
              </div>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
