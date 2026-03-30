export function LoadingCard({ label = "Cargando..." }: { label?: string }) {
  return (
    <div className="shell-card p-5">
      <div className="animate-pulse space-y-3">
        <div className="h-4 w-24 rounded-full bg-slate-200" />
        <div className="h-6 w-2/3 rounded-full bg-slate-200" />
        <div className="h-4 w-full rounded-full bg-slate-100" />
        <p className="text-sm text-slate-400">{label}</p>
      </div>
    </div>
  );
}
