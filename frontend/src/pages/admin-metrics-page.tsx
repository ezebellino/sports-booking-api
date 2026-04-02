import { BarChart3, CalendarRange, CircleAlert, DollarSign, MapPinned, Ticket } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { AppHeader } from "../components/app-header";
import { AdminNav } from "../components/admin-nav";
import { EmptyState } from "../components/empty-state";
import { LoadingCard } from "../components/loading-card";
import { SectionTitle } from "../components/section-title";
import { api, type AdminMetricsBucket } from "../lib/api";
import { dateInputDefault } from "../lib/format";

function offsetDate(days: number) {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return date.toISOString().slice(0, 10);
}

function toDateStartIso(value: string) {
  return value ? new Date(`${value}T00:00:00`).toISOString() : undefined;
}

function toDateEndIso(value: string) {
  return value ? new Date(`${value}T23:59:59`).toISOString() : undefined;
}

function percent(value: number) {
  return `${value.toFixed(1)}%`;
}

function money(value: number) {
  return new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: "ARS",
    maximumFractionDigits: 0,
  }).format(value);
}

function BucketTable({ title, rows, emptyLabel }: { title: string; rows: AdminMetricsBucket[]; emptyLabel: string }) {
  return (
    <div className="shell-card p-5">
      <h3 className="text-lg font-bold text-slate-950">{title}</h3>
      {!rows.length ? (
        <div className="mt-4">
          <EmptyState title="Todavía no hay datos" description={emptyLabel} />
        </div>
      ) : (
        <div className="mt-4 space-y-3">
          {rows.map((row) => (
            <article key={row.name} className="rounded-3xl border border-slate-200 bg-white p-4">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <p className="text-lg font-bold text-slate-950">{row.name}</p>
                  <p className="mt-1 text-sm text-slate-500">
                    {row.confirmed_bookings} confirmadas · {row.cancelled_bookings} canceladas · {row.total_timeslots} turnos
                  </p>
                </div>
                <div className="flex flex-wrap gap-2 text-xs font-semibold">
                  <span className="rounded-full bg-slate-100 px-3 py-1 text-slate-600">Ocupación {percent(row.occupancy_rate)}</span>
                  <span className="rounded-full bg-slate-100 px-3 py-1 text-slate-600">Cancelación {percent(row.cancellation_rate)}</span>
                  <span className="rounded-full bg-emerald-50 px-3 py-1 text-emerald-700">{money(row.estimated_revenue)}</span>
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

export function AdminMetricsPage() {
  const [dateFrom, setDateFrom] = useState(offsetDate(-7));
  const [dateTo, setDateTo] = useState(offsetDate(21));

  const metricsQuery = useQuery({
    queryKey: ["admin-metrics", dateFrom, dateTo],
    queryFn: () =>
      api.getAdminMetrics({
        dateFrom: toDateStartIso(dateFrom),
        dateTo: toDateEndIso(dateTo),
      }),
  });

  const highlights = useMemo(() => {
    const summary = metricsQuery.data?.summary;
    if (!summary) {
      return [];
    }

    return [
      {
        label: "Reservas confirmadas",
        value: String(summary.confirmed_bookings),
        help: `${summary.cancelled_bookings} canceladas en el mismo rango`,
        icon: Ticket,
      },
      {
        label: "Ocupación promedio",
        value: percent(summary.occupancy_rate),
        help: `${summary.spots_filled} de ${summary.spots_total} lugares ocupados`,
        icon: BarChart3,
      },
      {
        label: "Turnos próximos",
        value: String(summary.upcoming_timeslots),
        help: `${summary.active_timeslots} turnos activos en total`,
        icon: CalendarRange,
      },
      {
        label: "Facturación estimada",
        value: money(summary.estimated_revenue),
        help: "Estimación basada en reservas confirmadas y precio del turno",
        icon: DollarSign,
      },
    ];
  }, [metricsQuery.data?.summary]);

  return (
    <>
      <AppHeader />
      <section className="space-y-6">
        <AdminNav />

        <SectionTitle
          eyebrow="Admin"
          title="Métricas operativas"
          description="Seguí la demanda del complejo por rango de fechas, con foco en ocupación, cancelaciones y facturación estimada por sede y por deporte."
        />

        <div className="shell-card grid gap-3 p-4 md:grid-cols-[1fr_1fr_auto]">
          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-700" htmlFor="metrics-date-from">
              Desde
            </label>
            <input id="metrics-date-from" className="field" type="date" value={dateFrom} max={dateTo || undefined} onChange={(event) => setDateFrom(event.target.value)} />
          </div>
          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-700" htmlFor="metrics-date-to">
              Hasta
            </label>
            <input id="metrics-date-to" className="field" type="date" value={dateTo} min={dateFrom || undefined} onChange={(event) => setDateTo(event.target.value)} />
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-500 md:self-end">
            Referencia inicial sugerida: {dateInputDefault()}
          </div>
        </div>

        {metricsQuery.isLoading ? (
          <LoadingCard label="Preparando métricas del complejo..." />
        ) : metricsQuery.isError ? (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            <div className="flex items-start gap-2">
              <CircleAlert className="mt-0.5" size={16} />
              <span>{metricsQuery.error instanceof Error ? metricsQuery.error.message : "No pudimos cargar las métricas."}</span>
            </div>
          </div>
        ) : metricsQuery.data ? (
          <>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              {highlights.map((item) => {
                const Icon = item.icon;
                return (
                  <article key={item.label} className="shell-card p-5">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">{item.label}</p>
                        <p className="mt-3 text-3xl font-bold text-slate-950">{item.value}</p>
                      </div>
                      <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-100 text-slate-700">
                        <Icon size={20} />
                      </div>
                    </div>
                    <p className="mt-3 text-sm text-slate-500">{item.help}</p>
                  </article>
                );
              })}
            </div>

            <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
              <BucketTable
                title="Rendimiento por deporte"
                rows={metricsQuery.data.by_sport}
                emptyLabel="Cuando existan turnos en el rango elegido, acá vas a ver qué deporte concentra más reservas y cancelaciones."
              />
              <BucketTable
                title="Rendimiento por sede"
                rows={metricsQuery.data.by_venue}
                emptyLabel="Cuando existan turnos en el rango elegido, acá vas a ver cómo rinde cada sede del complejo."
              />
            </div>

            <div className="shell-card p-5">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-sky-100 text-sky-700">
                  <MapPinned size={18} />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-slate-950">Lectura rápida del período</h3>
                  <p className="text-sm text-slate-500">Resumen pensado para operación diaria, sin bajar a tablas técnicas.</p>
                </div>
              </div>

              <div className="mt-4 grid gap-3 md:grid-cols-3">
                <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                  <p className="font-semibold text-slate-900">Capacidad usada</p>
                  <p className="mt-1">Se ocuparon {metricsQuery.data.summary.spots_filled} de {metricsQuery.data.summary.spots_total} lugares publicados.</p>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                  <p className="font-semibold text-slate-900">Cancelaciones</p>
                  <p className="mt-1">La tasa de cancelación del período fue {percent(metricsQuery.data.summary.cancellation_rate)}.</p>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                  <p className="font-semibold text-slate-900">Oferta activa</p>
                  <p className="mt-1">Hay {metricsQuery.data.summary.active_timeslots} turnos activos dentro del rango y {metricsQuery.data.summary.upcoming_timeslots} todavía por jugarse.</p>
                </div>
              </div>
            </div>
          </>
        ) : (
          <EmptyState title="Todavía no hay métricas para mostrar" description="Probá ampliar el rango de fechas o cargá turnos y reservas para empezar a ver demanda real." />
        )}
      </section>
    </>
  );
}

