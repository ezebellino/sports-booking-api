import type { ReactNode } from "react";

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="shell-card flex flex-col items-start gap-3 p-5">
      <h3 className="text-lg font-bold text-slate-950">{title}</h3>
      <p className="text-sm leading-6 text-slate-500">{description}</p>
      {action}
    </div>
  );
}
