import { useQuery } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { CalendarCheck2, LoaderCircle, MapPinned, Shield, Ticket } from "lucide-react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { getBrandColor } from "../lib/branding";
import { buildTenantPath, useTenantPath, useTenantSlug } from "../lib/tenant";
import { useAuth } from "../modules/auth/auth-context";

export function AppHeader() {
  const navigate = useNavigate();
  const { canAccessAdmin, hasMultipleOrganizations, isAuthenticated, logout, switchOrganization, user } = useAuth();
  const tenantPath = useTenantPath();
  const tenantSlug = useTenantSlug();
  const contextQuery = useQuery({
    queryKey: ["request-organization-context", tenantSlug ?? "default"],
    queryFn: api.getRequestOrganizationContext,
    retry: false,
  });

  const roleLabel =
    user?.role === "admin" ? "Administrador" : user?.role === "staff" ? "Staff" : "Usuario";
  const adminNavLabel = user?.role === "staff" ? "Staff" : "Admin";
  const publicBrandLabel =
    contextQuery.data?.branding_name || contextQuery.data?.organization.name || "Complejo Demo";
  const organizationLabel = user?.organization_name ?? publicBrandLabel;
  const primaryColor = getBrandColor(contextQuery.data?.primary_color);
  const logoUrl = contextQuery.data?.logo_url ?? null;
  const titleLabel = tenantSlug ? publicBrandLabel : "Reservas deportivas";
  const subtitleLabel = tenantSlug ? "Reservas deportivas" : "Sports Booking";
  const [isSwitching, setIsSwitching] = useState(false);

  async function handleOrganizationChange(event: React.ChangeEvent<HTMLSelectElement>) {
    const nextOrganizationId = event.target.value;
    if (!nextOrganizationId || !user || nextOrganizationId === user.organization_id) {
      return;
    }

    setIsSwitching(true);
    try {
      const nextUser = await switchOrganization(nextOrganizationId);
      navigate(buildTenantPath("/explore", nextUser.organization_slug), { replace: true });
    } finally {
      setIsSwitching(false);
    }
  }

  return (
    <header className="mb-6 flex flex-col gap-4 pt-2">
      <div className="flex items-center justify-between gap-3">
        <Link to={tenantPath("/")} className="flex items-center gap-3" data-tour="app-brand">
          <div
            className="flex h-11 w-11 items-center justify-center overflow-hidden rounded-2xl bg-slate-900 text-white shadow-soft"
            style={primaryColor ? { backgroundColor: primaryColor } : undefined}
          >
            {logoUrl ? (
              <img src={logoUrl} alt={`Logo de ${publicBrandLabel}`} className="h-full w-full object-cover" />
            ) : (
              <Ticket size={20} />
            )}
          </div>
          <div>
            <p
              className="text-xs font-semibold uppercase tracking-[0.24em] text-skyline"
              style={primaryColor ? { color: primaryColor } : undefined}
            >
              {subtitleLabel}
            </p>
            <h1 className="text-lg font-extrabold text-slate-950">{titleLabel}</h1>
            {isAuthenticated && user ? (
              <p className="mt-0.5 text-xs font-medium text-slate-500">{organizationLabel}</p>
            ) : null}
          </div>
        </Link>

        <div className="hidden items-center gap-3 md:flex">
          <DesktopNavLink to={tenantPath("/explore")} icon={<MapPinned size={16} />} tourId="nav-explore">
            Explorar
          </DesktopNavLink>
          <DesktopNavLink to={tenantPath("/bookings")} icon={<CalendarCheck2 size={16} />} tourId="nav-bookings">
            Mis reservas
          </DesktopNavLink>
          {canAccessAdmin ? (
            <DesktopNavLink to={tenantPath("/admin/inventory")} icon={<Shield size={16} />} tourId="nav-admin">
              {adminNavLabel}
            </DesktopNavLink>
          ) : null}
          {isAuthenticated ? (
            <button className="btn-secondary" onClick={logout} type="button">
              Salir
            </button>
          ) : (
            <Link className="btn-primary" to={tenantPath("/login")}>
              Ingresar
            </Link>
          )}
        </div>
      </div>

      {isAuthenticated && user ? (
        <div className="shell-card flex items-center justify-between gap-3 px-4 py-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">Sesión activa</p>
            <div className="mt-1 flex flex-wrap items-center gap-2">
              <p className="text-sm font-semibold text-slate-800">{user.full_name || user.email}</p>
              <span
                className="inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-bold uppercase tracking-[0.16em]"
                style={
                  primaryColor
                    ? {
                        border: `1px solid ${primaryColor}`,
                        color: primaryColor,
                      }
                    : undefined
                }
              >
                {organizationLabel}
              </span>
              <span
                className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-bold uppercase tracking-[0.16em] ${
                  user.role === "admin" ? "bg-amber-100 text-amber-800" : "bg-slate-100 text-slate-600"
                }`}
              >
                <Shield size={12} />
                {roleLabel}
              </span>
            </div>
            <p className="mt-1 text-xs text-slate-500">
              {user.role === "admin"
                ? "Puede gestionar usuarios, sedes, canchas, turnos y próximas herramientas administrativas."
                : user.role === "staff"
                  ? "Puede operar sedes, canchas, turnos y métricas del complejo."
                  : "Puede registrarse, explorar turnos y administrar sus propias reservas."}
            </p>
            {hasMultipleOrganizations ? (
              <div className="mt-3 max-w-sm">
                <label className="mb-2 block text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">
                  Complejo activo
                </label>
                <div className="flex items-center gap-2">
                  <select
                    className="field py-2 text-sm"
                    value={user.organization_id ?? ""}
                    onChange={handleOrganizationChange}
                    disabled={isSwitching}
                  >
                    {user.memberships.map((membership) => (
                      <option key={membership.organization_id} value={membership.organization_id}>
                        {membership.organization_name} · {membership.role}
                      </option>
                    ))}
                  </select>
                  {isSwitching ? <LoaderCircle className="animate-spin text-slate-400" size={16} /> : null}
                </div>
              </div>
            ) : null}
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
  tourId,
}: {
  to: string;
  children: string;
  icon: ReactNode;
  tourId?: string;
}) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold transition ${
          isActive ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-white"
        }`
      }
      data-tour={tourId}
    >
      {icon}
      {children}
    </NavLink>
  );
}
