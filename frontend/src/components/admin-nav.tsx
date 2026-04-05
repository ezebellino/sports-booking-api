import { Building2 } from "lucide-react";
import { NavLink } from "react-router-dom";
import { useAuth } from "../modules/auth/auth-context";

export function AdminNav() {
  const {
    user,
    canManageOrganization,
    canManageStaff,
    canViewMetrics,
    canManageInventory,
    canManageTimeslots,
    canManageWhatsapp,
  } = useAuth();

  const organizationLabel = user?.organization_name ?? "Complejo Demo";
  const adminLinks = [
    canManageOrganization ? { to: "/admin/organization", label: "Complejo" } : null,
    canManageStaff ? { to: "/admin/staff", label: "Staff" } : null,
    canViewMetrics ? { to: "/admin/metrics", label: "Métricas" } : null,
    canManageInventory ? { to: "/admin/inventory", label: "Sedes y canchas" } : null,
    canManageTimeslots ? { to: "/admin/timeslots", label: "Turnos" } : null,
    canManageWhatsapp ? { to: "/admin/whatsapp", label: "WhatsApp" } : null,
  ].filter(Boolean) as Array<{ to: string; label: string }>;

  return (
    <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
      <nav className="flex flex-wrap gap-2" data-tour="admin-nav">
        {adminLinks.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            className={({ isActive }) =>
              `rounded-full px-4 py-2 text-sm font-semibold transition ${
                isActive ? "bg-slate-900 text-white" : "bg-white text-slate-600 hover:bg-slate-100"
              }`
            }
          >
            {link.label}
          </NavLink>
        ))}
      </nav>

      <div
        className="inline-flex items-center gap-2 self-start rounded-full border border-sky-200 bg-sky-50 px-4 py-2 text-sm font-semibold text-sky-800"
        data-tour="admin-tenant-badge"
      >
        <Building2 size={16} />
        Administrando {organizationLabel}
      </div>
    </div>
  );
}
