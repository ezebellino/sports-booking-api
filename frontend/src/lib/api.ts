import { clearTokens, getStoredTokens, storeTokens } from "./storage";

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

export type User = {
  id: string;
  email: string;
  full_name: string | null;
  role: "admin" | "user";
};

export type Sport = {
  id: string;
  name: string;
  description: string | null;
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
  availability_status: "available" | "few_left" | "full" | "inactive" | "expired";
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
  register: (input: { email: string; password: string; full_name: string }) =>
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

  listSports: () => request<Sport[]>("/sports"),

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

