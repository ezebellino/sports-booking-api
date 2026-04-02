import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CircleAlert, LoaderCircle } from "lucide-react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { AppHeader } from "../components/app-header";
import { api } from "../lib/api";
import {
  normalizeEmail,
  normalizePhone,
  validateEmail,
  validateFullName,
  validatePassword,
  validateWhatsappNumber,
} from "../lib/validation";
import { useAuth } from "../modules/auth/auth-context";

type RegisterErrors = {
  fullName?: string;
  email?: string;
  password?: string;
  whatsappNumber?: string;
};

export function RegisterPage() {
  const navigate = useNavigate();
  const { isAuthenticated, register } = useAuth();
  const contextQuery = useQuery({
    queryKey: ["request-organization-context"],
    queryFn: api.getRequestOrganizationContext,
  });
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [whatsappNumber, setWhatsappNumber] = useState("");
  const [whatsappOptIn, setWhatsappOptIn] = useState(false);
  const [errors, setErrors] = useState<RegisterErrors>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const brandLabel = contextQuery.data?.branding_name ?? contextQuery.data?.organization.name ?? "el complejo";

  const helperText = useMemo(() => {
    if (loading) {
      return "Estamos creando tu cuenta y preparando el ingreso automático.";
    }

    return `Podés dejar tu WhatsApp ahora o cargarlo después. Solo lo usaremos para avisos de reserva y cancelación de ${brandLabel}.`;
  }, [brandLabel, loading]);

  if (isAuthenticated) {
    return <Navigate to="/explore" replace />;
  }

  function clearFieldError(field: keyof RegisterErrors) {
    setErrors((current) => ({ ...current, [field]: undefined }));
    setSubmitError(null);
  }

  function validateForm() {
    const nextErrors: RegisterErrors = {
      fullName: validateFullName(fullName),
      email: validateEmail(email),
      password: validatePassword(password),
      whatsappNumber: validateWhatsappNumber(whatsappNumber),
    };

    setErrors(nextErrors);
    return !nextErrors.fullName && !nextErrors.email && !nextErrors.password && !nextErrors.whatsappNumber;
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitError(null);

    if (!validateForm()) {
      return;
    }

    setLoading(true);

    try {
      await register({
        full_name: fullName.trim(),
        email: normalizeEmail(email),
        password: password.trim(),
        whatsapp_number: normalizePhone(whatsappNumber) || null,
        whatsapp_opt_in: whatsappOptIn,
      });
      navigate("/explore");
    } catch (submitError) {
      setSubmitError(submitError instanceof Error ? submitError.message : "No pudimos crear la cuenta.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <AppHeader />
      <section className="mx-auto grid w-full max-w-5xl gap-4 lg:grid-cols-[0.95fr_1.05fr]">
        <div className="shell-card p-6 sm:p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-skyline">Registro</p>
          <h2 className="mt-3 text-3xl font-black tracking-tight text-slate-950">Creá tu acceso</h2>
          <p className="mt-3 text-sm leading-6 text-slate-500">
            Registrate para reservar dentro de {brandLabel}. Después del alta vas a entrar automáticamente para llegar
            directo a explorar turnos.
          </p>
        </div>

        <form className="shell-card space-y-4 p-6 sm:p-8" onSubmit={handleSubmit} noValidate>
          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-700" htmlFor="full-name">
              Nombre completo
            </label>
            <input
              id="full-name"
              className={`field ${errors.fullName ? "field-error" : ""}`}
              type="text"
              placeholder="Ezequiel Bellino"
              value={fullName}
              onChange={(event) => {
                setFullName(event.target.value);
                clearFieldError("fullName");
              }}
              required
            />
            {errors.fullName ? <p className="mt-2 text-sm text-rose-700">{errors.fullName}</p> : null}
          </div>

          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-700" htmlFor="register-email">
              Email
            </label>
            <input
              id="register-email"
              className={`field ${errors.email ? "field-error" : ""}`}
              type="email"
              autoComplete="email"
              placeholder="vos@correo.com"
              value={email}
              onChange={(event) => {
                setEmail(event.target.value);
                clearFieldError("email");
              }}
              required
            />
            {errors.email ? <p className="mt-2 text-sm text-rose-700">{errors.email}</p> : null}
          </div>

          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-700" htmlFor="register-password">
              Contraseña
            </label>
            <input
              id="register-password"
              className={`field ${errors.password ? "field-error" : ""}`}
              type="password"
              autoComplete="new-password"
              placeholder="Al menos 8 caracteres"
              value={password}
              onChange={(event) => {
                setPassword(event.target.value);
                clearFieldError("password");
              }}
              required
            />
            {errors.password ? <p className="mt-2 text-sm text-rose-700">{errors.password}</p> : null}
          </div>

          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-700" htmlFor="register-whatsapp">
              WhatsApp
            </label>
            <input
              id="register-whatsapp"
              className={`field ${errors.whatsappNumber ? "field-error" : ""}`}
              type="tel"
              placeholder="5491122334455"
              value={whatsappNumber}
              onChange={(event) => {
                setWhatsappNumber(event.target.value);
                clearFieldError("whatsappNumber");
              }}
            />
            {errors.whatsappNumber ? <p className="mt-2 text-sm text-rose-700">{errors.whatsappNumber}</p> : null}
          </div>

          <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
            <input type="checkbox" checked={whatsappOptIn} onChange={(event) => setWhatsappOptIn(event.target.checked)} />
            Quiero recibir confirmaciones y cancelaciones por WhatsApp.
          </label>

          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
            {helperText}
          </div>

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
                Creando cuenta...
              </span>
            ) : (
              "Crear cuenta"
            )}
          </button>

          <p className="text-center text-sm text-slate-500">
            ¿Ya tenés usuario?{" "}
            <Link className="font-semibold text-slate-900" to="/login">
              Ingresar
            </Link>
          </p>
        </form>
      </section>
    </>
  );
}
