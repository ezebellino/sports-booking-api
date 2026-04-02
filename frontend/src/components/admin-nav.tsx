import { NavLink } from "react-router-dom";

const adminLinks = [
  { to: "/admin/metrics", label: "Métricas" },
  { to: "/admin/inventory", label: "Sedes y canchas" },
  { to: "/admin/timeslots", label: "Turnos" },
  { to: "/admin/whatsapp", label: "WhatsApp" },
];

export function AdminNav() {
  return (
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
  );
}
