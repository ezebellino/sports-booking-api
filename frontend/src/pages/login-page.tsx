import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { AppHeader } from "../components/app-header";
import { useAuth } from "../modules/auth/auth-context";

export function LoginPage() {
  const navigate = useNavigate();
  const { isAuthenticated, login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (isAuthenticated) {
    return <Navigate to="/explore" replace />;
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await login({ email, password });
      navigate("/explore");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "No pudimos iniciar sesión");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <AppHeader />
      <section className="mx-auto grid w-full max-w-5xl gap-4 lg:grid-cols-[0.95fr_1.05fr]">
        <div className="shell-card p-6 sm:p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-skyline">Acceso</p>
          <h2 className="mt-3 text-3xl font-black tracking-tight text-slate-950">
            Entrá a tu cuenta
          </h2>
          <p className="mt-3 text-sm leading-6 text-slate-500">
            Tu backend ya usa JWT con refresh. En el frontend dejamos sesión persistida para que la
            app se sienta continua, sobre todo en mobile.
          </p>
        </div>

        <form className="shell-card space-y-4 p-6 sm:p-8" onSubmit={handleSubmit}>
          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-700" htmlFor="email">
              Email
            </label>
            <input
              id="email"
              className="field"
              type="email"
              autoComplete="email"
              placeholder="vos@correo.com"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-700" htmlFor="password">
              Contraseña
            </label>
            <input
              id="password"
              className="field"
              type="password"
              autoComplete="current-password"
              placeholder="Tu contraseña"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </div>

          {error ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {error}
            </div>
          ) : null}

          <button className="btn-primary w-full" type="submit" disabled={loading}>
            {loading ? "Ingresando..." : "Ingresar"}
          </button>

          <p className="text-center text-sm text-slate-500">
            ¿No tenés cuenta? {" "}
            <Link className="font-semibold text-slate-900" to="/register">
              Crear cuenta
            </Link>
          </p>
        </form>
      </section>
    </>
  );
}
