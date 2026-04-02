import { Building2 } from "lucide-react";
import { NavLink } from "react-router-dom";
import { useAuth } from "../modules/auth/auth-context";

const adminLinks = [
  { to: "/admin/organization", label: "Complejo" },
  { to: "/admin/staff", label: "Staff" },
  { to: "/admin/metrics", label: "Métricas" },
  { to: "/admin/inventory", label: "Sedes y canchas" },
  { to: "/admin/timeslots", label: "Turnos" },
  { to: "/admin/whatsapp", label: "WhatsApp" },
];

export function AdminNav() {
  const { user } = useAuth();
  const organizationLabel = user?.organization_name ?? "Complejo Demo";

  return (
    <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
      <nav className="flex flex-wrap gap-2">
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

      <div className="inline-flex items-center gap-2 self-start rounded-full border border-sky-200 bg-sky-50 px-4 py-2 text-sm font-semibold text-sky-800">
        <Building2 size={16} />
        Administrando {organizationLabel}
      </div>
    </div>
  );
}
