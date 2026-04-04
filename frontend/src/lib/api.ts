import { clearTokens, getStoredTokens, storeTokens } from "./storage";

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

export type User = {
  id: string;
  email: string;
  full_name: string | null;
  role: "admin" | "staff" | "user";
  organization_id: string | null;
  organization_name: string | null;
  organization_slug: string | null;
  whatsapp_number: string | null;
  whatsapp_opt_in: boolean;
};

export type Organization = {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
};

export type OrganizationRequestContext = {
  organization: Organization;
  branding_name: string | null;
  logo_url: string | null;
  primary_color: string | null;
};

export type OrganizationSettings = {
  organization_id: string;
  branding_name: string | null;
  logo_url: string | null;
  primary_color: string | null;
  booking_min_lead_minutes: number | null;
  cancellation_min_lead_minutes: number | null;
  whatsapp_provider: string | null;
  whatsapp_phone_number_id: string | null;
  whatsapp_template_language: string | null;
  whatsapp_template_booking_confirmed: string | null;
  whatsapp_template_booking_cancelled: string | null;
  whatsapp_recipient_override: string | null;
  has_whatsapp_access_token: boolean;
};

export type StaffInvitation = {
  id: string;
  organization_id: string;
  email: string;
  full_name: string | null;
  role: "admin" | "staff" | "user";
  status: string;
  invite_token: string;
  expires_at: string;
  accepted_at: string | null;
};

export type Sport = {
  id: string;
  name: string;
  description: string | null;
  booking_min_lead_minutes: number | null;
  cancellation_min_lead_minutes: number | null;
};

export type OrganizationSport = {
  sport: Sport;
  is_enabled: boolean;
};

export type Venue = {
  id: string;
  name: string;
  address: string | null;
  timezone: string;
  allowed_sport_id: string | null;
};

export type Court = {
  id: string;
  venue_id: string;
  sport_id: string;
  name: string;
  indoor: boolean | null;
  is_active: boolean;
};

export type TimeSlot = {
  id: string;
  court_id: string;
  starts_at: string;
  ends_at: string;
  capacity: number;
  price: number | null;
  is_active: boolean;
  confirmed_bookings: number;
  remaining_spots: number;
  availability_status: "available" | "few_left" | "full" | "inactive" | "expired" | "booking_closed";
  policy_summary: string | null;
};

export type AdminMetricsBucket = {
  name: string;
  total_timeslots: number;
  active_timeslots: number;
  confirmed_bookings: number;
  cancelled_bookings: number;
  spots_total: number;
  spots_filled: number;
  occupancy_rate: number;
  cancellation_rate: number;
  estimated_revenue: number;
};

export type AdminMetrics = {
  summary: {
    date_from: string | null;
    date_to: string | null;
    total_timeslots: number;
    active_timeslots: number;
    upcoming_timeslots: number;
    confirmed_bookings: number;
    cancelled_bookings: number;
    spots_total: number;
    spots_filled: number;
    occupancy_rate: number;
    cancellation_rate: number;
    estimated_revenue: number;
  };
  by_sport: AdminMetricsBucket[];
  by_venue: AdminMetricsBucket[];
};

export type NotificationStatus = {
  provider: string;
  enabled: boolean;
  configured: boolean;
  ready_for_live_send: boolean;
  has_access_token: boolean;
  has_phone_number_id: boolean;
  recipient_override: string | null;
  template_language: string;
  booking_confirmed_template: string | null;
  booking_cancelled_template: string | null;
  has_booking_confirmed_template: boolean;
  has_booking_cancelled_template: boolean;
  test_mode: boolean;
  missing_items: string[];
  checks: Array<{
    key: string;
    label: string;
    ok: boolean;
    detail: string;
    severity: "required" | "optional";
  }>;
};

export type HolidayCalendarItem = {
  date: string;
  local_name: string;
  name: string;
  country_code: string;
  global_holiday: boolean;
  counties: string[] | null;
  launch_year: number | null;
  types: string[];
};

export type HolidayCalendar = {
  country_code: string;
  year: number;
  month: number | null;
  holidays: HolidayCalendarItem[];
};

export type OrganizationOnboardingResult = {
  organization: Organization;
  user_id: string;
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
};

export type StaffInvitationAcceptanceResult = {
  organization: Organization;
  user_id: string;
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
};

export type BookingPolicy = {
  sport_id: string | null;
  sport_name: string | null;
  uses_default_policy: boolean;
  min_booking_lead_minutes: number;
  cancellation_min_lead_minutes: number;
  booking_message: string;
  cancellation_message: string;
  admin_summary: string;
};

export type TimeSlotBulkCreateResult = {
  created_count: number;
  skipped_count: number;
  created_slots: TimeSlot[];
  skipped_reasons: string[];
};

export type Booking = {
  id: string;
  user_id: string;
  timeslot_id: string;
  status: "confirmed" | "cancelled";
  created_at: string;
  updated_at: string;
};

export type BookingDetail = Booking & {
  can_cancel: boolean;
  cancellation_deadline: string | null;
  cancellation_policy_message: string | null;
  booking_policy_summary: string | null;
  timeslot: TimeSlot & {
    court: Court & {
      venue: Venue;
      sport: Sport;
    };
  };
};

type RequestOptions = {
  method?: string;
  body?: BodyInit | null;
  headers?: HeadersInit;
  auth?: boolean;
  retry?: boolean;
};

async function refreshAccessToken() {
  const stored = getStoredTokens();

  if (!stored?.refreshToken) {
    throw new Error("No refresh token");
  }

  const response = await fetch(`${API_URL}/auth/refresh`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ refresh_token: stored.refreshToken }),
  });

  if (!response.ok) {
    clearTokens();
    throw new Error("Refresh token inválido");
  }

  const data = (await response.json()) as {
    access_token: string;
    refresh_token: string;
  };

  storeTokens({
    accessToken: data.access_token,
    refreshToken: data.refresh_token,
  });

  return data.access_token;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { auth = false, retry = true, ...rest } = options;
  const headers = new Headers(rest.headers);

  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }

  if (auth) {
    const stored = getStoredTokens();
    if (stored?.accessToken) {
      headers.set("Authorization", `Bearer ${stored.accessToken}`);
    }
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...rest,
    headers,
  });

  if (response.status === 401 && auth && retry) {
    const newAccessToken = await refreshAccessToken();
    headers.set("Authorization", `Bearer ${newAccessToken}`);
    return request<T>(path, { ...options, headers, retry: false });
  }

  if (!response.ok) {
    const payload = await safeJson(response);
    const detail =
      typeof payload === "object" && payload && "detail" in payload
        ? String(payload.detail)
        : "No pudimos completar la solicitud";
    throw new Error(detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

async function safeJson(response: Response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

export const api = {
  register: (input: { email: string; password: string; full_name: string; whatsapp_number?: string | null; whatsapp_opt_in?: boolean }) =>
    request<User>("/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),

  login: async (input: { email: string; password: string }) => {
    const params = new URLSearchParams();
    params.set("username", input.email);
    params.set("password", input.password);

    return request<{ access_token: string; refresh_token: string }>("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: params,
    });
  },

  me: () => request<User>("/auth/me", { auth: true }),

  updateMe: (input: { full_name?: string | null; whatsapp_number?: string | null; whatsapp_opt_in?: boolean }) =>
    request<User>("/auth/me", {
      method: "PATCH",
      auth: true,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),

  onboardOrganization: (input: {
    organization_name: string;
    organization_slug?: string | null;
    admin_full_name: string;
    admin_email: string;
    admin_password: string;
    whatsapp_number?: string | null;
    whatsapp_opt_in?: boolean;
  }) =>
    request<OrganizationOnboardingResult>("/organizations/onboard", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),

  getCurrentOrganization: () => request<Organization>("/organizations/current", { auth: true }),

  getRequestOrganizationContext: () => request<OrganizationRequestContext>("/organizations/request-context"),

  updateCurrentOrganization: (input: { name?: string; slug?: string; is_active?: boolean }) =>
    request<Organization>("/organizations/current", {
      method: "PATCH",
      auth: true,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),

  getCurrentOrganizationSettings: () =>
    request<OrganizationSettings>("/organizations/current/settings", { auth: true }),

  updateCurrentOrganizationSettings: (input: {
    branding_name?: string | null;
    logo_url?: string | null;
    primary_color?: string | null;
    booking_min_lead_minutes?: number | null;
    cancellation_min_lead_minutes?: number | null;
    whatsapp_provider?: string | null;
    whatsapp_access_token?: string | null;
    whatsapp_phone_number_id?: string | null;
    whatsapp_template_language?: string | null;
    whatsapp_template_booking_confirmed?: string | null;
    whatsapp_template_booking_cancelled?: string | null;
    whatsapp_recipient_override?: string | null;
  }) =>
    request<OrganizationSettings>("/organizations/current/settings", {
      method: "PATCH",
      auth: true,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),

  listStaffInvitations: () =>
    request<StaffInvitation[]>("/organizations/current/staff-invitations", { auth: true }),

  createStaffInvitation: (input: {
    email: string;
    full_name?: string | null;
    role: "admin" | "staff" | "user";
    expires_in_days?: number;
  }) =>
    request<StaffInvitation>("/organizations/current/staff-invitations", {
      method: "POST",
      auth: true,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),

  acceptStaffInvitation: (input: {
    token: string;
    full_name?: string | null;
    password: string;
    whatsapp_number?: string | null;
    whatsapp_opt_in?: boolean;
  }) =>
    request<StaffInvitationAcceptanceResult>("/organizations/staff-invitations/accept", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),

  listSports: () => request<Sport[]>("/sports"),

  listSportsCatalog: () => request<Sport[]>("/sports/catalog", { auth: true }),

  createSport: (input: {
    name: string;
    description?: string | null;
    booking_min_lead_minutes?: number | null;
    cancellation_min_lead_minutes?: number | null;
  }) =>
    request<Sport>("/sports", {
      method: "POST",
      auth: true,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),

  listCurrentOrganizationSports: () =>
    request<OrganizationSport[]>("/organizations/current/sports", { auth: true }),

  updateCurrentOrganizationSports: (enabledSportIds: string[]) =>
    request<OrganizationSport[]>("/organizations/current/sports", {
      method: "PATCH",
      auth: true,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled_sport_ids: enabledSportIds }),
    }),

  updateSport: (
    sportId: string,
    input: {
      name?: string;
      description?: string | null;
      booking_min_lead_minutes?: number | null;
      cancellation_min_lead_minutes?: number | null;
    },
  ) =>
    request<Sport>(`/sports/${sportId}`, {
      method: "PATCH",
      auth: true,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),

  getAdminMetrics: (params: { dateFrom?: string; dateTo?: string }) => {
    const searchParams = new URLSearchParams();
    if (params.dateFrom) {
      searchParams.set("date_from", params.dateFrom);
    }
    if (params.dateTo) {
      searchParams.set("date_to", params.dateTo);
    }
    const suffix = searchParams.toString();
    return request<AdminMetrics>(suffix ? `/admin/metrics?${suffix}` : "/admin/metrics", { auth: true });
  },

  getNotificationStatus: () => request<NotificationStatus>("/admin/notification-status", { auth: true }),

  getAdminHolidays: (params: { year: number; month?: number; countryCode?: string }) => {
    const searchParams = new URLSearchParams();
    searchParams.set("year", String(params.year));
    if (params.month) {
      searchParams.set("month", String(params.month));
    }
    if (params.countryCode) {
      searchParams.set("country_code", params.countryCode);
    }
    return request<HolidayCalendar>(`/admin/holidays?${searchParams.toString()}`, { auth: true });
  },

  listVenues: (sportId?: string | null) =>
    request<Venue[]>("/venues?limit=100").then((venues) =>
      sportId ? venues.filter((venue) => !venue.allowed_sport_id || venue.allowed_sport_id === sportId) : venues,
    ),

  createVenue: (input: { name: string; address: string | null; timezone: string; allowed_sport_id: string | null }) =>
    request<Venue>("/venues", {
      method: "POST",
      auth: true,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),

  updateVenue: (venueId: string, input: { name?: string; address?: string | null; timezone?: string; allowed_sport_id?: string | null }) =>
    request<Venue>(`/venues/${venueId}`, {
      method: "PATCH",
      auth: true,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),

  deleteVenue: (venueId: string) =>
    request<void>(`/venues/${venueId}`, {
      method: "DELETE",
      auth: true,
    }),

  listCourts: (params: { venueId?: string | null; sportId?: string | null }) => {
    const searchParams = new URLSearchParams();
    searchParams.set("limit", "100");
    if (params.venueId) {
      searchParams.set("venue_id", params.venueId);
    }
    if (params.sportId) {
      searchParams.set("sport_id", params.sportId);
    }
    return request<Court[]>(`/courts?${searchParams.toString()}`);
  },

  createCourt: (input: { venue_id: string; sport_id: string; name: string; indoor: boolean | null; is_active: boolean }) =>
    request<Court>("/courts", {
      method: "POST",
      auth: true,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),

  updateCourt: (courtId: string, input: { venue_id?: string; sport_id?: string; name?: string; indoor?: boolean | null; is_active?: boolean }) =>
    request<Court>(`/courts/${courtId}`, {
      method: "PATCH",
      auth: true,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),

  deleteCourt: (courtId: string) =>
    request<void>(`/courts/${courtId}`, {
      method: "DELETE",
      auth: true,
    }),

  listTimeslots: (params: { courtId?: string | null; dateFrom?: string; dateTo?: string }) => {
    const searchParams = new URLSearchParams();
    searchParams.set("limit", "100");
    if (params.courtId) {
      searchParams.set("court_id", params.courtId);
    }
    if (params.dateFrom) {
      searchParams.set("date_from", params.dateFrom);
    }
    if (params.dateTo) {
      searchParams.set("date_to", params.dateTo);
    }
    return request<TimeSlot[]>(`/timeslots?${searchParams.toString()}`);
  },

  createTimeslot: (input: {
    court_id: string;
    starts_at: string;
    ends_at: string;
    capacity: number;
    price: number | null;
    is_active: boolean;
  }) =>
    request<TimeSlot>("/timeslots", {
      method: "POST",
      auth: true,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),

  bulkCreateTimeslots: (input: {
    court_ids: string[];
    window_starts_at: string;
    window_ends_at: string;
    slot_minutes: number;
    capacity: number;
    price: number | null;
    is_active: boolean;
  }) =>
    request<TimeSlotBulkCreateResult>("/admin/timeslots/bulk", {
      method: "POST",
      auth: true,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),

  updateTimeslot: (timeslotId: string, input: {
    starts_at?: string;
    ends_at?: string;
    capacity?: number;
    price?: number | null;
    is_active?: boolean;
  }) =>
    request<TimeSlot>(`/timeslots/${timeslotId}`, {
      method: "PATCH",
      auth: true,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),

  listBookingPolicies: (sportId?: string | null) => {
    const searchParams = new URLSearchParams();
    if (sportId) {
      searchParams.set("sport_id", sportId);
    }
    const suffix = searchParams.toString();
    return request<BookingPolicy>(suffix ? `/bookings/policies?${suffix}` : "/bookings/policies");
  },

  listBookings: () => request<BookingDetail[]>("/bookings", { auth: true }),

  createBooking: (timeslotId: string) =>
    request<Booking>("/bookings", {
      method: "POST",
      auth: true,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ timeslot_id: timeslotId }),
    }),

  cancelBooking: (bookingId: string) =>
    request<Booking>(`/bookings/${bookingId}/cancel`, {
      method: "PATCH",
      auth: true,
    }),
};
