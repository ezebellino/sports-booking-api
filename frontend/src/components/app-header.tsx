import type { ReactNode } from "react";
import { CalendarCheck2, MapPinned, Ticket } from "lucide-react";
import { Link, NavLink } from "react-router-dom";
import { useAuth } from "../modules/auth/auth-context";

export function AppHeader() {
  const { isAuthenticated, logout, user } = useAuth();

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
          </div>
        </Link>

        <div className="hidden items-center gap-3 md:flex">
          <DesktopNavLink to="/explore" icon={<MapPinned size={16} />}>
            Explorar
          </DesktopNavLink>
          <DesktopNavLink to="/bookings" icon={<CalendarCheck2 size={16} />}>
            Mis reservas
          </DesktopNavLink>
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
            <p className="text-sm font-semibold text-slate-800">
              {user.full_name || user.email}
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
