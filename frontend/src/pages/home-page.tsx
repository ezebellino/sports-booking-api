import { useQuery } from "@tanstack/react-query";
import { ArrowRight, CalendarRange, Map, ShieldCheck, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";
import { AppHeader } from "../components/app-header";
import { LoadingCard } from "../components/loading-card";
import { SectionTitle } from "../components/section-title";
import { api } from "../lib/api";
import { useAuth } from "../modules/auth/auth-context";

export function HomePage() {
  const { isAuthenticated } = useAuth();
  const sportsQuery = useQuery({ queryKey: ["sports"], queryFn: api.listSports });
  const venuesQuery = useQuery({ queryKey: ["venues"], queryFn: () => api.listVenues(null) });

  return (
    <>
      <AppHeader />

      <section className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
        <div className="shell-card overflow-hidden p-6 sm:p-8">
          <div className="inline-flex items-center gap-2 rounded-full bg-orange-100 px-3 py-1 text-xs font-bold uppercase tracking-[0.2em] text-orange-700">
            <Sparkles size={14} />
            Mobile-first booking flow
          </div>
          <h2 className="mt-5 max-w-xl text-4xl font-black tracking-tight text-slate-950 sm:text-5xl">
            Reservá una cancha en pocos toques, sin perderte entre turnos.
          </h2>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-600 sm:text-base">
            Armamos una experiencia clara para elegir deporte, sede, cancha y horario desde el
            celular. El backend ya lo tenías bien planteado; ahora lo estamos llevando a una
            interfaz usable y lista para iterar.
          </p>

          <div className="mt-6 flex flex-col gap-3 sm:flex-row">
            <Link className="btn-primary" to="/explore">
              Empezar a explorar
              <ArrowRight className="ml-2" size={16} />
            </Link>
            <Link className="btn-secondary" to={isAuthenticated ? "/bookings" : "/login"}>
              {isAuthenticated ? "Ver mis reservas" : "Ingresar"}
            </Link>
          </div>

          <div className="mt-8 grid gap-3 sm:grid-cols-3">
            <MetricCard label="Deportes" value={String(sportsQuery.data?.length ?? 0)} icon={<ShieldCheck size={18} />} />
            <MetricCard label="Sedes" value={String(venuesQuery.data?.length ?? 0)} icon={<Map size={18} />} />
            <MetricCard label="Flujo" value="1 sola vista" icon={<CalendarRange size={18} />} />
          </div>
        </div>

        <div className="grid gap-4">
          {sportsQuery.isLoading ? (
            <LoadingCard label="Traemos deportes desde tu API..." />
          ) : (
            <div className="shell-card p-6">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">
                Deporte primero
              </p>
              <h3 className="mt-2 text-xl font-bold text-slate-950">Entradas rápidas</h3>
              <div className="mt-4 flex flex-wrap gap-2">
                {sportsQuery.data?.slice(0, 6).map((sport) => (
                  <Link key={sport.id} to={`/explore?sport=${sport.id}`} className="chip hover:border-slate-300">
                    {sport.name}
                  </Link>
                ))}
              </div>
            </div>
          )}

          <div className="shell-card p-6">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">
              Qué sigue
            </p>
            <ul className="mt-3 space-y-3 text-sm leading-6 text-slate-600">
              <li>Login y registro con sesión persistida.</li>
              <li>Exploración por sede, cancha y fecha con filtros móviles.</li>
              <li>Reserva efectiva usando `/bookings` y vista personal de agenda.</li>
            </ul>
          </div>
        </div>
      </section>

      <section className="mt-8 grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <SectionTitle
            eyebrow="Flujo"
            title="Un frontend pensado para lo que ya expone tu backend"
            description="No inventamos endpoints nuevos para arrancar. La UI compone deportes, sedes, canchas y turnos desde los recursos existentes y deja base para sumar admins, pagos y cancelaciones."
          />
        </div>
        <div className="shell-card p-6">
          <p className="text-sm font-semibold text-slate-700">Base técnica sugerida</p>
          <p className="mt-2 text-sm leading-6 text-slate-500">
            React + Vite + TypeScript + Tailwind + React Query. Liviano para empezar, sólido para
            crecer.
          </p>
        </div>
      </section>
    </>
  );
}

function MetricCard({
  label,
  value,
  icon,
}: {
  label: string;
  value: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="rounded-3xl border border-slate-200 bg-slate-50 p-4">
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-slate-500">{label}</span>
        <span className="text-slate-400">{icon}</span>
      </div>
      <p className="mt-3 text-3xl font-black text-slate-950">{value}</p>
    </div>
  );
}
