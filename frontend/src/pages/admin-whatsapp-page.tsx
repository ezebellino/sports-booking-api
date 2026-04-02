import { BellRing, CheckCircle2, MessageCircleMore, Smartphone, Wrench } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
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
  const notificationStatusQuery = useQuery({
    queryKey: ["admin-whatsapp-status"],
    queryFn: api.getNotificationStatus,
  });

  if (notificationStatusQuery.isLoading) {
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
          description="Controlá si la integración está lista para producción, qué templates usa el sistema y qué falta completar antes de enviar mensajes reales a los clientes."
        />

        <div className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
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
                      <div className="flex items-center gap-2">
                        <StatusPill ok={check.ok} label={check.ok ? "OK" : check.severity === "optional" ? "Opcional" : "Pendiente"} />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
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
                <p>
                  Recomendación: hacé una reserva de prueba y una cancelación de prueba después de cada cambio de template o credencial.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
