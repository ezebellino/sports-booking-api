import { CircleAlert, LoaderCircle } from "lucide-react";
import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { AppHeader } from "../components/app-header";
import { normalizeEmail, normalizePhone, validateEmail, validateFullName, validatePassword } from "../lib/validation";
import { useAuth } from "../modules/auth/auth-context";

type OnboardingErrors = {
  organizationName?: string;
  adminFullName?: string;
  adminEmail?: string;
  adminPassword?: string;
};

export function StartComplexPage() {
  const navigate = useNavigate();
  const { isAuthenticated, onboardOrganization } = useAuth();
  const [organizationName, setOrganizationName] = useState("");
  const [organizationSlug, setOrganizationSlug] = useState("");
  const [adminFullName, setAdminFullName] = useState("");
  const [adminEmail, setAdminEmail] = useState("");
  const [adminPassword, setAdminPassword] = useState("");
  const [whatsappNumber, setWhatsappNumber] = useState("");
  const [whatsappOptIn, setWhatsappOptIn] = useState(false);
  const [errors, setErrors] = useState<OnboardingErrors>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (isAuthenticated) {
    return <Navigate to="/admin/organization" replace />;
  }

  function validateForm() {
    const nextErrors: OnboardingErrors = {
      organizationName: organizationName.trim() ? undefined : "El complejo necesita un nombre.",
      adminFullName: validateFullName(adminFullName),
      adminEmail: validateEmail(adminEmail),
      adminPassword: validatePassword(adminPassword),
    };
    setErrors(nextErrors);
    return !nextErrors.organizationName && !nextErrors.adminFullName && !nextErrors.adminEmail && !nextErrors.adminPassword;
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitError(null);

    if (!validateForm()) {
      return;
    }

    setLoading(true);
    try {
      await onboardOrganization({
        organization_name: organizationName.trim(),
        organization_slug: organizationSlug.trim() || null,
        admin_full_name: adminFullName.trim(),
        admin_email: normalizeEmail(adminEmail),
        admin_password: adminPassword.trim(),
        whatsapp_number: normalizePhone(whatsappNumber) || null,
        whatsapp_opt_in: whatsappOptIn,
      });
      navigate("/admin/organization");
    } catch (submissionError) {
      setSubmitError(submissionError instanceof Error ? submissionError.message : "No pudimos crear el complejo.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <AppHeader />
      <section className="mx-auto grid w-full max-w-6xl gap-4 lg:grid-cols-[0.95fr_1.05fr]">
        <div className="shell-card p-6 sm:p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-skyline">Onboarding SaaS</p>
          <h2 className="mt-3 text-3xl font-black tracking-tight text-slate-950">
            Lanzá un complejo nuevo en pocos minutos
          </h2>
          <p className="mt-3 text-sm leading-6 text-slate-500">
            Este alta crea la organización, configura al primer administrador y te deja ingresado
            directamente para seguir con sedes, canchas, turnos y políticas.
          </p>
        </div>

        <form className="shell-card space-y-4 p-6 sm:p-8" onSubmit={handleSubmit} noValidate>
          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-700" htmlFor="organization-name">
              Nombre del complejo
            </label>
            <input
              id="organization-name"
              className="field"
              value={organizationName}
              onChange={(event) => setOrganizationName(event.target.value)}
              placeholder="Ej. Complejo Norte"
            />
            {errors.organizationName ? <p className="mt-2 text-sm text-rose-700">{errors.organizationName}</p> : null}
          </div>

          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-700" htmlFor="organization-slug">
              Identificador opcional
            </label>
            <input
              id="organization-slug"
              className="field"
              value={organizationSlug}
              onChange={(event) => setOrganizationSlug(event.target.value)}
              placeholder="complejo-norte"
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-700" htmlFor="admin-full-name">
              Nombre del administrador
            </label>
            <input
              id="admin-full-name"
              className="field"
              value={adminFullName}
              onChange={(event) => setAdminFullName(event.target.value)}
              placeholder="Ezequiel Bellino"
            />
            {errors.adminFullName ? <p className="mt-2 text-sm text-rose-700">{errors.adminFullName}</p> : null}
          </div>

          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-700" htmlFor="admin-email">
              Email del administrador
            </label>
            <input
              id="admin-email"
              className="field"
              type="email"
              value={adminEmail}
              onChange={(event) => setAdminEmail(event.target.value)}
              placeholder="admin@complejo.com"
            />
            {errors.adminEmail ? <p className="mt-2 text-sm text-rose-700">{errors.adminEmail}</p> : null}
          </div>

          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-700" htmlFor="admin-password">
              Contraseña inicial
            </label>
            <input
              id="admin-password"
              className="field"
              type="password"
              value={adminPassword}
              onChange={(event) => setAdminPassword(event.target.value)}
              placeholder="Al menos 8 caracteres"
            />
            {errors.adminPassword ? <p className="mt-2 text-sm text-rose-700">{errors.adminPassword}</p> : null}
          </div>

          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-700" htmlFor="admin-whatsapp">
              WhatsApp del administrador
            </label>
            <input
              id="admin-whatsapp"
              className="field"
              type="tel"
              value={whatsappNumber}
              onChange={(event) => setWhatsappNumber(event.target.value)}
              placeholder="5491122334455"
            />
          </div>

          <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
            <input type="checkbox" checked={whatsappOptIn} onChange={(event) => setWhatsappOptIn(event.target.checked)} />
            Quiero habilitar notificaciones por WhatsApp para el administrador inicial.
          </label>

          {submitError ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              <div className="flex items-start gap-2">
                <CircleAlert className="mt-0.5" size={16} />
                <span>{submitError}</span>
              </div>
            </div>
          ) : null}

          <button className="btn-primary w-full" type="submit" disabled={loading}>
            {loading ? (
              <span className="inline-flex items-center gap-2">
                <LoaderCircle className="animate-spin" size={16} />
                Creando complejo...
              </span>
            ) : (
              "Crear complejo y continuar"
            )}
          </button>

          <p className="text-center text-sm text-slate-500">
            ¿Ya tenés un complejo activo? <Link className="font-semibold text-slate-900" to="/login">Ingresar</Link>
          </p>
        </form>
      </section>
    </>
  );
}
