import { Building2, CalendarDays, Compass, House, LogIn, Ticket } from "lucide-react";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./modules/auth/auth-context";
import { AdminInventoryPage } from "./pages/admin-inventory-page";
import { AdminTimeslotsPage } from "./pages/admin-timeslots-page";
import { AdminWhatsappPage } from "./pages/admin-whatsapp-page";
import { ExplorePage } from "./pages/explore-page";
import { HomePage } from "./pages/home-page";
import { LoginPage } from "./pages/login-page";
import { MyBookingsPage } from "./pages/my-bookings-page";
import { RegisterPage } from "./pages/register-page";

function ProtectedRoute({ children }: { children: React.ReactElement }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-hero px-4">
        <div className="shell-card w-full max-w-sm p-6 text-center text-sm text-slate-500">
          Cargando sesión...
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

function AdminRoute({ children }: { children: React.ReactElement }) {
  const { isAuthenticated, isAdmin, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-hero px-4">
        <div className="shell-card w-full max-w-sm p-6 text-center text-sm text-slate-500">
          Validando permisos...
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (!isAdmin) {
    return <Navigate to="/explore" replace />;
  }

  return children;
}

function AppShell() {
  const { isAuthenticated, isAdmin } = useAuth();

  return (
    <div className="min-h-screen bg-hero">
      <main className="mx-auto flex min-h-screen w-full max-w-6xl flex-col px-4 pb-24 pt-4 sm:px-6 lg:px-8">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/explore" element={<ExplorePage />} />
          <Route
            path="/bookings"
            element={
              <ProtectedRoute>
                <MyBookingsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/inventory"
            element={
              <AdminRoute>
                <AdminInventoryPage />
              </AdminRoute>
            }
          />
          <Route
            path="/admin/timeslots"
            element={
              <AdminRoute>
                <AdminTimeslotsPage />
              </AdminRoute>
            }
          />
          <Route
            path="/admin/whatsapp"
            element={
              <AdminRoute>
                <AdminWhatsappPage />
              </AdminRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>

      <nav className="fixed inset-x-0 bottom-0 z-20 border-t border-slate-200/80 bg-white/95 px-4 py-3 backdrop-blur md:hidden">
        <div className="mx-auto flex max-w-md items-center justify-between gap-2">
          <MobileLink to="/" label="Inicio" icon={House} />
          <MobileLink to="/explore" label="Explorar" icon={Compass} />
          {isAdmin ? (
            <MobileLink to="/admin/inventory" label="Admin" icon={Building2} />
          ) : (
            <MobileLink to="/bookings" label="Reservas" icon={Ticket} />
          )}
          <MobileLink
            to={isAuthenticated ? "/bookings" : "/login"}
            label={isAuthenticated ? "Agenda" : "Entrar"}
            icon={isAuthenticated ? CalendarDays : LogIn}
          />
        </div>
      </nav>
    </div>
  );
}

function MobileLink({
  to,
  label,
  icon: Icon,
}: {
  to: string;
  label: string;
  icon: typeof House;
}) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `flex min-w-0 flex-1 flex-col items-center gap-1 rounded-2xl px-2 py-2 text-[11px] font-semibold transition ${
          isActive ? "bg-slate-900 text-white" : "text-slate-500"
        }`
      }
    >
      <Icon size={18} />
      <span>{label}</span>
    </NavLink>
  );
}

export default function App() {
  return <AppShell />;
}
