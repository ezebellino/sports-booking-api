import type { ReactNode } from "react";
import { CalendarCheck2, MapPinned, Shield, Ticket } from "lucide-react";
import { Link, NavLink } from "react-router-dom";
import { useAuth } from "../modules/auth/auth-context";

export function AppHeader() {
  const { isAdmin, isAuthenticated, logout, user } = useAuth();
  const roleLabel = user?.role === "admin" ? "Administrador" : "Usuario";
  const organizationLabel = user?.organization_name ?? "Complejo Demo";

  return (
    <header className="mb-6 flex flex-col gap-4 pt-2">
      <div className="flex items-center justify-between gap-3">
        <Link to="/" className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-900 text-white shadow-soft">
            <Ticket size={20} />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-skyline">
              Sports Booking
            </p>
            <h1 className="text-lg font-extrabold text-slate-950">Reservas deportivas</h1>
            {isAuthenticated && user ? (
              <p className="mt-0.5 text-xs font-medium text-slate-500">{organizationLabel}</p>
            ) : null}
          </div>
        </Link>

        <div className="hidden items-center gap-3 md:flex">
          <DesktopNavLink to="/explore" icon={<MapPinned size={16} />}>
            Explorar
          </DesktopNavLink>
          <DesktopNavLink to="/bookings" icon={<CalendarCheck2 size={16} />}>
            Mis reservas
          </DesktopNavLink>
          {isAdmin ? (
            <DesktopNavLink to="/admin/inventory" icon={<Shield size={16} />}>
              Admin
            </DesktopNavLink>
          ) : null}
          {isAuthenticated ? (
            <button className="btn-secondary" onClick={logout} type="button">
              Salir
            </button>
          ) : (
            <Link className="btn-primary" to="/login">
              Ingresar
            </Link>
          )}
        </div>
      </div>

      {isAuthenticated && user ? (
        <div className="shell-card flex items-center justify-between gap-3 px-4 py-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">
              Sesión activa
            </p>
            <div className="mt-1 flex flex-wrap items-center gap-2">
              <p className="text-sm font-semibold text-slate-800">{user.full_name || user.email}</p>
              <span className="inline-flex items-center rounded-full bg-sky-100 px-2.5 py-1 text-[11px] font-bold uppercase tracking-[0.16em] text-sky-700">
                {organizationLabel}
              </span>
              <span
                className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-bold uppercase tracking-[0.16em] ${
                  user.role === "admin"
                    ? "bg-amber-100 text-amber-800"
                    : "bg-slate-100 text-slate-600"
                }`}
              >
                <Shield size={12} />
                {roleLabel}
              </span>
            </div>
            <p className="mt-1 text-xs text-slate-500">
              {user.role === "admin"
                ? "Puede gestionar usuarios, sedes, canchas, turnos y próximas herramientas administrativas."
                : "Puede registrarse, explorar turnos y administrar sus propias reservas."}
            </p>
          </div>
          <button className="btn-secondary md:hidden" onClick={logout} type="button">
            Salir
          </button>
        </div>
      ) : null}
    </header>
  );
}

function DesktopNavLink({
  to,
  children,
  icon,
}: {
  to: string;
  children: string;
  icon: ReactNode;
}) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold transition ${
          isActive ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-white"
        }`
      }
    >
      {icon}
      {children}
    </NavLink>
  );
}
