import { useParams } from "react-router-dom";

const RESERVED_PUBLIC_SEGMENTS = new Set([
  "",
  "login",
  "register",
  "explore",
  "bookings",
  "admin",
  "start-complex",
  "accept-invite",
]);

export function sanitizeTenantSlug(value: string | null | undefined) {
  if (!value) {
    return null;
  }
  const normalized = value.trim().toLowerCase();
  return normalized || null;
}

export function buildTenantPath(path: string, tenantSlug?: string | null) {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const normalizedTenantSlug = sanitizeTenantSlug(tenantSlug);

  if (!normalizedTenantSlug) {
    return normalizedPath;
  }

  return normalizedPath === "/"
    ? `/${normalizedTenantSlug}`
    : `/${normalizedTenantSlug}${normalizedPath}`;
}

export function detectTenantSlugFromPath(pathname: string) {
  const firstSegment = pathname.split("/").filter(Boolean)[0] ?? "";
  const normalized = sanitizeTenantSlug(firstSegment);
  if (!normalized || RESERVED_PUBLIC_SEGMENTS.has(normalized)) {
    return null;
  }
  return normalized;
}

export function useTenantSlug() {
  const params = useParams();
  return sanitizeTenantSlug(params.organizationSlug);
}

export function useTenantPath() {
  const tenantSlug = useTenantSlug();
  return (path: string) => buildTenantPath(path, tenantSlug);
}
