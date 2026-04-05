import { useQuery } from "@tanstack/react-query";
import { Building2, CalendarDays, Compass, House, LogIn, Ticket } from "lucide-react";
import { NavLink, Navigate, Outlet, Route, Routes } from "react-router-dom";
import { api } from "./lib/api";
import { buildTenantPath, useTenantPath, useTenantSlug } from "./lib/tenant";
import { useAuth } from "./modules/auth/auth-context";
import { AdminInventoryPage } from "./pages/admin-inventory-page";
import { AdminMetricsPage } from "./pages/admin-metrics-page";
import { AdminOrganizationPage } from "./pages/admin-organization-page";
import { AdminStaffPage } from "./pages/admin-staff-page";
import { AdminTimeslotsPage } from "./pages/admin-timeslots-page";
import { AdminWhatsappPage } from "./pages/admin-whatsapp-page";
import { AcceptInvitePage } from "./pages/accept-invite-page";
import { ExplorePage } from "./pages/explore-page";
import { HomePage } from "./pages/home-page";
import { LoginPage } from "./pages/login-page";
import { MyBookingsPage } from "./pages/my-bookings-page";
import { RegisterPage } from "./pages/register-page";
import { StartComplexPage } from "./pages/start-complex-page";

function ProtectedRoute({ children }: { children: React.ReactElement }) {
  const { isAuthenticated, loading } = useAuth();
  const tenantPath = useTenantPath();

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
    return <Navigate to={tenantPath("/login")} replace />;
  }

  return children;
}

function AdminRoute({ children }: { children: React.ReactElement }) {
  const { isAuthenticated, canAccessAdmin, loading } = useAuth();
  const tenantPath = useTenantPath();

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
    return <Navigate to={tenantPath("/login")} replace />;
  }

  if (!canAccessAdmin) {
    return <Navigate to={tenantPath("/explore")} replace />;
  }

  return children;
}

function FullAdminRoute({ children }: { children: React.ReactElement }) {
  const { isAuthenticated, isAdmin, loading } = useAuth();
  const tenantPath = useTenantPath();

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
    return <Navigate to={tenantPath("/login")} replace />;
  }

  if (!isAdmin) {
    return <Navigate to={tenantPath("/admin/metrics")} replace />;
  }

  return children;
}

function AppShellLayout() {
  const { canAccessAdmin, isAuthenticated, user } = useAuth();
  const tenantPath = useTenantPath();
  const adminLabel = user?.role === "staff" ? "Staff" : "Admin";

  return (
    <div className="min-h-screen bg-hero">
      <main className="mx-auto flex min-h-screen w-full max-w-6xl flex-col px-4 pb-24 pt-4 sm:px-6 lg:px-8">
        <Outlet />
      </main>

      <nav className="fixed inset-x-0 bottom-0 z-20 border-t border-slate-200/80 bg-white/95 px-4 py-3 backdrop-blur md:hidden">
        <div className="mx-auto flex max-w-md items-center justify-between gap-2">
          <MobileLink to={tenantPath("/")} label="Inicio" icon={House} />
          <MobileLink to={tenantPath("/explore")} label="Explorar" icon={Compass} />
          {canAccessAdmin ? (
            <MobileLink to={tenantPath("/admin/metrics")} label={adminLabel} icon={Building2} />
          ) : (
            <MobileLink to={tenantPath("/bookings")} label="Reservas" icon={Ticket} />
          )}
          <MobileLink
            to={isAuthenticated ? tenantPath("/bookings") : tenantPath("/login")}
            label={isAuthenticated ? "Agenda" : "Entrar"}
            icon={isAuthenticated ? CalendarDays : LogIn}
          />
        </div>
      </nav>
    </div>
  );
}

function TenantRouteBoundary() {
  const tenantSlug = useTenantSlug();
  const contextQuery = useQuery({
    queryKey: ["request-organization-context", tenantSlug],
    queryFn: api.getRequestOrganizationContext,
    enabled: Boolean(tenantSlug),
    retry: false,
  });

  if (!tenantSlug) {
    return <Outlet />;
  }

  if (contextQuery.isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-hero px-4">
        <div className="shell-card w-full max-w-lg p-8 text-center">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-skyline">Cargando complejo</p>
          <h2 className="mt-3 text-2xl font-black text-slate-950">Resolviendo {tenantSlug}</h2>
          <p className="mt-3 text-sm text-slate-500">Estamos validando el acceso público a este complejo.</p>
        </div>
      </div>
    );
  }

  if (contextQuery.isError) {
    const message =
      contextQuery.error instanceof Error ? contextQuery.error.message : "No pudimos encontrar este complejo.";

    return (
      <div className="flex min-h-screen items-center justify-center bg-hero px-4">
        <div className="shell-card w-full max-w-xl p-8 text-center">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-skyline">Complejo no disponible</p>
          <h2 className="mt-3 text-3xl font-black text-slate-950">No encontramos “{tenantSlug}”</h2>
          <p className="mt-3 text-sm leading-6 text-slate-500">
            {message === "Complejo no encontrado"
              ? "Revisá el enlace o volvé al acceso principal para entrar al complejo correcto."
              : message}
          </p>
          <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-center">
            <NavLink className="btn-primary" to={buildTenantPath("/", null)}>
              Ir al acceso principal
            </NavLink>
            <NavLink className="btn-secondary" to="/start-complex">
              Crear un complejo
            </NavLink>
          </div>
        </div>
      </div>
    );
  }

  return <Outlet />;
}

function renderSharedAppRoutes() {
  return (
    <>
      <Route index element={<HomePage />} />
      <Route path="login" element={<LoginPage />} />
      <Route path="register" element={<RegisterPage />} />
      <Route path="explore" element={<ExplorePage />} />
      <Route
        path="bookings"
        element={
          <ProtectedRoute>
            <MyBookingsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="admin/organization"
        element={
          <FullAdminRoute>
            <AdminOrganizationPage />
          </FullAdminRoute>
        }
      />
      <Route
        path="admin/staff"
        element={
          <FullAdminRoute>
            <AdminStaffPage />
          </FullAdminRoute>
        }
      />
      <Route
        path="admin/metrics"
        element={
          <AdminRoute>
            <AdminMetricsPage />
          </AdminRoute>
        }
      />
      <Route
        path="admin/inventory"
        element={
          <AdminRoute>
            <AdminInventoryPage />
          </AdminRoute>
        }
      />
      <Route
        path="admin/timeslots"
        element={
          <AdminRoute>
            <AdminTimeslotsPage />
          </AdminRoute>
        }
      />
      <Route
        path="admin/whatsapp"
        element={
          <FullAdminRoute>
            <AdminWhatsappPage />
          </FullAdminRoute>
        }
      />
    </>
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
  return (
    <Routes>
      <Route path="/start-complex" element={<StartComplexPage />} />
      <Route path="/accept-invite" element={<AcceptInvitePage />} />

      <Route element={<AppShellLayout />}>
        {renderSharedAppRoutes()}
      </Route>

      <Route path="/:organizationSlug" element={<TenantRouteBoundary />}>
        <Route element={<AppShellLayout />}>
          {renderSharedAppRoutes()}
        </Route>
      </Route>

      <Route path="*" element={<Navigate to={buildTenantPath("/", null)} replace />} />
    </Routes>
  );
}
