import { CircleAlert, LoaderCircle } from "lucide-react";
import { useMemo, useState } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { AppHeader } from "../components/app-header";
import {
  normalizePhone,
  validateFullName,
  validatePassword,
  validateWhatsappNumber,
} from "../lib/validation";
import { useAuth } from "../modules/auth/auth-context";

type InviteErrors = {
  fullName?: string;
  password?: string;
  whatsappNumber?: string;
};

export function AcceptInvitePage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { acceptStaffInvitation, isAuthenticated } = useAuth();

  const token = useMemo(() => searchParams.get("token")?.trim() ?? "", [searchParams]);
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [whatsappNumber, setWhatsappNumber] = useState("");
  const [whatsappOptIn, setWhatsappOptIn] = useState(false);
  const [errors, setErrors] = useState<InviteErrors>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (isAuthenticated) {
    return <Navigate to="/explore" replace />;
  }

  function validateForm() {
    const nextErrors: InviteErrors = {
      fullName: validateFullName(fullName),
      password: validatePassword(password),
      whatsappNumber: validateWhatsappNumber(whatsappNumber),
    };
    setErrors(nextErrors);
    return !nextErrors.fullName && !nextErrors.password && !nextErrors.whatsappNumber;
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitError(null);

    if (!token) {
      setSubmitError("El link de invitación no es válido.");
      return;
    }

    if (!validateForm()) {
      return;
    }

    setLoading(true);
    try {
      await acceptStaffInvitation({
        token,
        full_name: fullName.trim(),
        password: password.trim(),
        whatsapp_number: normalizePhone(whatsappNumber) || null,
        whatsapp_opt_in: whatsappOptIn,
      });
      navigate("/explore");
    } catch (submissionError) {
      setSubmitError(submissionError instanceof Error ? submissionError.message : "No pudimos aceptar la invitación.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <AppHeader />
      <section className="mx-auto grid w-full max-w-5xl gap-4 lg:grid-cols-[0.9fr_1.1fr]">
        <div className="shell-card p-6 sm:p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-skyline">Invitación de staff</p>
          <h2 className="mt-3 text-3xl font-black tracking-tight text-slate-950">Sumate a un complejo ya configurado</h2>
          <p className="mt-3 text-sm leading-6 text-slate-500">
            Este alta crea tu cuenta dentro del complejo que te invitó. Después vas a entrar con tu propio usuario y permisos.
          </p>
          <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
            {token ? "El link de invitación está listo para activarse." : "Falta el token de invitación en el link."}
          </div>
        </div>

        <form className="shell-card space-y-4 p-6 sm:p-8" onSubmit={handleSubmit} noValidate>
          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-700" htmlFor="invite-full-name">
              Nombre completo
            </label>
            <input
              id="invite-full-name"
              className="field"
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
              placeholder="Tu nombre y apellido"
            />
            {errors.fullName ? <p className="mt-2 text-sm text-rose-700">{errors.fullName}</p> : null}
          </div>

          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-700" htmlFor="invite-password">
              Contraseña
            </label>
            <input
              id="invite-password"
              className="field"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Al menos 8 caracteres"
            />
            {errors.password ? <p className="mt-2 text-sm text-rose-700">{errors.password}</p> : null}
          </div>

          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-700" htmlFor="invite-whatsapp">
              WhatsApp
            </label>
            <input
              id="invite-whatsapp"
              className="field"
              type="tel"
              value={whatsappNumber}
              onChange={(event) => setWhatsappNumber(event.target.value)}
              placeholder="5491122334455"
            />
            {errors.whatsappNumber ? <p className="mt-2 text-sm text-rose-700">{errors.whatsappNumber}</p> : null}
          </div>

          <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
            <input type="checkbox" checked={whatsappOptIn} onChange={(event) => setWhatsappOptIn(event.target.checked)} />
            Quiero recibir notificaciones operativas por WhatsApp.
          </label>

          {submitError ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              <div className="flex items-start gap-2">
                <CircleAlert className="mt-0.5" size={16} />
                <span>{submitError}</span>
              </div>
            </div>
          ) : null}

          <button className="btn-primary w-full" type="submit" disabled={loading || !token}>
            {loading ? (
              <span className="inline-flex items-center gap-2">
                <LoaderCircle className="animate-spin" size={16} />
                Activando acceso...
              </span>
            ) : (
              "Aceptar invitación"
            )}
          </button>

          <p className="text-center text-sm text-slate-500">
            ¿Ya tenés una cuenta?{" "}
            <Link className="font-semibold text-slate-900" to="/login">
              Ingresar
            </Link>
          </p>
        </form>
      </section>
    </>
  );
}
