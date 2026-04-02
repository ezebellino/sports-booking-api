import { useQuery } from "@tanstack/react-query";
import { ArrowRight, CalendarRange, Map, ShieldCheck, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";
import { AppHeader } from "../components/app-header";
import { LoadingCard } from "../components/loading-card";
import { SectionTitle } from "../components/section-title";
import { api } from "../lib/api";
import { useAuth } from "../modules/auth/auth-context";

export function HomePage() {
  const { isAuthenticated, isAdmin, user } = useAuth();
  const sportsQuery = useQuery({ queryKey: ["sports"], queryFn: api.listSports });
  const venuesQuery = useQuery({ queryKey: ["venues"], queryFn: () => api.listVenues(null) });
  const organizationLabel = user?.organization_name ?? "Complejo Demo";

  return (
    <>
      <AppHeader />

      <section className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
        <div className="shell-card overflow-hidden p-6 sm:p-8">
          <div className="inline-flex items-center gap-2 rounded-full bg-orange-100 px-3 py-1 text-xs font-bold uppercase tracking-[0.2em] text-orange-700">
            <Sparkles size={14} />
            Sports booking listo para operar
          </div>
          <h2 className="mt-5 max-w-xl text-4xl font-black tracking-tight text-slate-950 sm:text-5xl">
            Reservá una cancha en pocos toques, con un flujo claro de punta a punta.
          </h2>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-600 sm:text-base">
            La experiencia está pensada para celular: primero elegís deporte, después sede,
            luego cancha y por último el turno disponible. Si sos administrador, además tenés
            herramientas para generar y editar bloques completos de horarios.
          </p>
          {isAuthenticated ? (
            <div className="mt-4 inline-flex items-center rounded-full bg-sky-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-sky-700">
              Complejo activo: {organizationLabel}
            </div>
          ) : null}

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
            <MetricCard label="Perfil" value={isAdmin ? "Admin" : "Usuario"} icon={<CalendarRange size={18} />} />
          </div>
        </div>

        <div className="grid gap-4">
          {sportsQuery.isLoading ? (
            <LoadingCard label="Cargando accesos rápidos..." />
          ) : (
            <div className="shell-card p-6">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">Deporte primero</p>
              <h3 className="mt-2 text-xl font-bold text-slate-950">Accesos rápidos</h3>
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
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">Qué podés hacer</p>
            <ul className="mt-3 space-y-3 text-sm leading-6 text-slate-600">
              <li>Entrar con tu cuenta y mantener la sesión activa.</li>
              <li>Explorar por sede, cancha y fecha con un flujo simple.</li>
              <li>Reservar turnos y revisar tu agenda personal con la hora local de cada sede.</li>
              {isAuthenticated ? <li>Operar dentro del complejo activo sin mezclar datos de otras sedes o clientes.</li> : null}
              <li>{isAdmin ? "Administrar turnos masivos, edición y control por cancha." : "Ver el panel admin cuando tu rol tenga permisos."}</li>
            </ul>
          </div>
        </div>
      </section>

      <section className="mt-8 grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <SectionTitle
            eyebrow="Plataforma"
            title="Una base lista para reservas reales y operación diaria"
            description="El frontend ya conversa con tus recursos actuales de deportes, sedes, canchas, turnos, autenticación y reservas. Sobre esa base estamos sumando experiencia admin, validaciones y automatizaciones para el día a día del complejo."
          />
        </div>
        <div className="shell-card p-6">
          <p className="text-sm font-semibold text-slate-700">Operación clara</p>
          <p className="mt-2 text-sm leading-6 text-slate-500">
            La app ya muestra disponibilidad, historial y referencia horaria por sede para reducir errores de operación y reservas.
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
