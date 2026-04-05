import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CircleAlert, LoaderCircle } from "lucide-react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { AppHeader } from "../components/app-header";
import { api } from "../lib/api";
import { getBrandColor } from "../lib/branding";
import { useTenantPath, useTenantSlug } from "../lib/tenant";
import { normalizeEmail, validateEmail, validatePassword } from "../lib/validation";
import { useAuth } from "../modules/auth/auth-context";

type LoginErrors = {
  email?: string;
  password?: string;
};

export function LoginPage() {
  const navigate = useNavigate();
  const { isAuthenticated, login } = useAuth();
  const tenantSlug = useTenantSlug();
  const tenantPath = useTenantPath();
  const contextQuery = useQuery({
    queryKey: ["request-organization-context", tenantSlug ?? "default"],
    queryFn: api.getRequestOrganizationContext,
    retry: false,
  });
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<LoginErrors>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const brandLabel =
    contextQuery.data?.branding_name ?? contextQuery.data?.organization.name ?? "el complejo";
  const primaryColor = getBrandColor(contextQuery.data?.primary_color);

  const helperText = useMemo(() => {
    if (loading) {
      return "Estamos validando tus credenciales y preparando tu sesión.";
    }

    return `Usá el mismo email y contraseña que registraste en ${brandLabel}.`;
  }, [brandLabel, loading]);

  if (isAuthenticated) {
    return <Navigate to={tenantPath("/explore")} replace />;
  }

  function clearFieldError(field: keyof LoginErrors) {
    setErrors((current) => ({ ...current, [field]: undefined }));
    setSubmitError(null);
  }

  function validateForm() {
    const nextErrors: LoginErrors = {
      email: validateEmail(email),
      password: validatePassword(password),
    };

    setErrors(nextErrors);
    return !nextErrors.email && !nextErrors.password;
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitError(null);

    if (!validateForm()) {
      return;
    }

    setLoading(true);

    try {
      await login({ email: normalizeEmail(email), password: password.trim() });
      navigate(tenantPath("/explore"));
    } catch (submissionError) {
      setSubmitError(submissionError instanceof Error ? submissionError.message : "No pudimos iniciar sesión.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <AppHeader />
      <section className="mx-auto grid w-full max-w-5xl gap-4 lg:grid-cols-[0.95fr_1.05fr]">
        <div className="shell-card p-6 sm:p-8">
          <p
            className="text-xs font-semibold uppercase tracking-[0.2em] text-skyline"
            style={primaryColor ? { color: primaryColor } : undefined}
          >
            Acceso
          </p>
          <h2 className="mt-3 text-3xl font-black tracking-tight text-slate-950">Entrá a tu cuenta</h2>
          <p className="mt-3 text-sm leading-6 text-slate-500">
            Ingresá para operar dentro de {brandLabel}. La sesión queda persistida para que la app se sienta continua,
            sobre todo en mobile.
          </p>
          <div
            className="mt-4 inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em]"
            style={primaryColor ? { border: `1px solid ${primaryColor}`, color: primaryColor } : undefined}
          >
            Complejo: {brandLabel}
          </div>
        </div>

        <form className="shell-card space-y-4 p-6 sm:p-8" onSubmit={handleSubmit} noValidate>
          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-700" htmlFor="email">
              Email
            </label>
            <input
              id="email"
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
            <label className="mb-2 block text-sm font-semibold text-slate-700" htmlFor="password">
              Contraseña
            </label>
            <input
              id="password"
              className={`field ${errors.password ? "field-error" : ""}`}
              type="password"
              autoComplete="current-password"
              placeholder="Tu contraseña"
              value={password}
              onChange={(event) => {
                setPassword(event.target.value);
                clearFieldError("password");
              }}
              required
            />
            {errors.password ? <p className="mt-2 text-sm text-rose-700">{errors.password}</p> : null}
          </div>

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
                Ingresando...
              </span>
            ) : (
              "Ingresar"
            )}
          </button>

          <p className="text-center text-sm text-slate-500">
            ¿No tenés cuenta?{" "}
            <Link className="font-semibold text-slate-900" to={tenantPath("/register")}>
              Crear cuenta
            </Link>
          </p>
        </form>
      </section>
    </>
  );
}
