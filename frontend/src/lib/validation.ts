export function normalizeEmail(value: string) {
  return value.trim().toLowerCase();
}

export function normalizePhone(value: string) {
  return value.replace(/[^\d+]/g, "").trim();
}

export function validateEmail(value: string) {
  const email = normalizeEmail(value);

  if (!email) {
    return "Ingresá tu email.";
  }

  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailPattern.test(email)) {
    return "Ingresá un email válido.";
  }

  return undefined;
}

export function validatePassword(value: string) {
  const password = value.trim();

  if (!password) {
    return "Ingresá tu contraseña.";
  }

  if (password.length < 8) {
    return "La contraseña debe tener al menos 8 caracteres.";
  }

  return undefined;
}

export function validateFullName(value: string) {
  const fullName = value.trim();

  if (!fullName) {
    return "Ingresá tu nombre completo.";
  }

  if (fullName.length < 3) {
    return "El nombre debe tener al menos 3 caracteres.";
  }

  return undefined;
}

export function validateWhatsappNumber(value: string) {
  const phone = normalizePhone(value);

  if (!phone) {
    return undefined;
  }

  if (!/^\+?\d{8,15}$/.test(phone)) {
    return "Ingresá un WhatsApp válido con código de país.";
  }

  return undefined;
}
