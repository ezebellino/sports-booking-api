export function isHexColor(value: string | null | undefined) {
  return Boolean(value && /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(value.trim()));
}

export function getBrandColor(value: string | null | undefined) {
  return isHexColor(value) ? value!.trim() : null;
}
