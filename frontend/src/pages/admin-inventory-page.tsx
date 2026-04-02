import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Building2,
  CircleAlert,
  LoaderCircle,
  MapPinned,
  PencilLine,
  Plus,
  Save,
  Shield,
  Trash2,
  Volleyball,
} from "lucide-react";
import { useMemo, useState } from "react";
import { AdminNav } from "../components/admin-nav";
import { AdminSportPolicies } from "../components/admin-sport-policies";
import { AppHeader } from "../components/app-header";
import { EmptyState } from "../components/empty-state";
import { LoadingCard } from "../components/loading-card";
import { SectionTitle } from "../components/section-title";
import { api, type Court, type Venue } from "../lib/api";
import { confirmDestructiveAction } from "../lib/dialog";

const DEFAULT_TIMEZONE = "America/Argentina/Buenos_Aires";

function normalizeOptionalText(value: string) {
  const trimmed = value.trim();
  return trimmed.length ? trimmed : null;
}

export function AdminInventoryPage() {
  const queryClient = useQueryClient();
  const [venueName, setVenueName] = useState("");
  const [venueAddress, setVenueAddress] = useState("");
  const [venueTimezone, setVenueTimezone] = useState(DEFAULT_TIMEZONE);
  const [venueAllowedSportId, setVenueAllowedSportId] = useState("");
  const [venueError, setVenueError] = useState<string | null>(null);
  const [venueSuccess, setVenueSuccess] = useState<string | null>(null);
  const [editingVenueId, setEditingVenueId] = useState<string | null>(null);
  const [editVenueName, setEditVenueName] = useState("");
  const [editVenueAddress, setEditVenueAddress] = useState("");
  const [editVenueTimezone, setEditVenueTimezone] = useState(DEFAULT_TIMEZONE);
  const [editVenueAllowedSportId, setEditVenueAllowedSportId] = useState("");
  const [courtName, setCourtName] = useState("");
  const [courtVenueId, setCourtVenueId] = useState("");
  const [courtSportId, setCourtSportId] = useState("");
  const [courtIndoor, setCourtIndoor] = useState("indoor");
  const [courtIsActive, setCourtIsActive] = useState(true);
  const [courtError, setCourtError] = useState<string | null>(null);
  const [courtSuccess, setCourtSuccess] = useState<string | null>(null);
  const [editingCourtId, setEditingCourtId] = useState<string | null>(null);
  const [editCourtName, setEditCourtName] = useState("");
  const [editCourtVenueId, setEditCourtVenueId] = useState("");
  const [editCourtSportId, setEditCourtSportId] = useState("");
  const [editCourtIndoor, setEditCourtIndoor] = useState("indoor");
  const [editCourtIsActive, setEditCourtIsActive] = useState(true);
  const [venueSearch, setVenueSearch] = useState("");
  const [venueSportFilter, setVenueSportFilter] = useState("");
  const [courtSearch, setCourtSearch] = useState("");
  const [courtVenueFilter, setCourtVenueFilter] = useState("");
  const [courtSportFilter, setCourtSportFilter] = useState("");
  const [courtStatusFilter, setCourtStatusFilter] = useState("all");

  const sportsQuery = useQuery({
    queryKey: ["sports"],
    queryFn: api.listSports,
  });

  const venuesQuery = useQuery({
    queryKey: ["venues", "admin-inventory"],
    queryFn: () => api.listVenues(null),
  });

  const courtsQuery = useQuery({
    queryKey: ["courts", "admin-inventory"],
    queryFn: () => api.listCourts({}),
  });

  const sportsById = useMemo(
    () => new Map((sportsQuery.data ?? []).map((sport) => [sport.id, sport])),
    [sportsQuery.data],
  );
  const venuesById = useMemo(
    () => new Map((venuesQuery.data ?? []).map((venue) => [venue.id, venue])),
    [venuesQuery.data],
  );

  const availableSportsForCourt = useMemo(() => {
    const selectedVenue = courtVenueId ? venuesById.get(courtVenueId) ?? null : null;
    if (!selectedVenue?.allowed_sport_id) {
      return sportsQuery.data ?? [];
    }
    return (sportsQuery.data ?? []).filter((sport) => sport.id === selectedVenue.allowed_sport_id);
  }, [courtVenueId, sportsQuery.data, venuesById]);

  const availableEditSportsForCourt = useMemo(() => {
    const selectedVenue = editCourtVenueId ? venuesById.get(editCourtVenueId) ?? null : null;
    if (!selectedVenue?.allowed_sport_id) {
      return sportsQuery.data ?? [];
    }
    return (sportsQuery.data ?? []).filter((sport) => sport.id === selectedVenue.allowed_sport_id);
  }, [editCourtVenueId, sportsQuery.data, venuesById]);

  const filteredVenues = useMemo(() => {
    const search = venueSearch.trim().toLowerCase();

    return (venuesQuery.data ?? []).filter((venue) => {
      const matchesSearch =
        !search ||
        venue.name.toLowerCase().includes(search) ||
        (venue.address ?? "").toLowerCase().includes(search);
      const matchesSport = !venueSportFilter || venue.allowed_sport_id === venueSportFilter;
      return matchesSearch && matchesSport;
    });
  }, [venueSearch, venueSportFilter, venuesQuery.data]);

  const filteredCourts = useMemo(() => {
    const search = courtSearch.trim().toLowerCase();

    return (courtsQuery.data ?? []).filter((court) => {
      const venue = venuesById.get(court.venue_id);
      const sport = sportsById.get(court.sport_id);
      const matchesSearch =
        !search ||
        court.name.toLowerCase().includes(search) ||
        (venue?.name ?? "").toLowerCase().includes(search) ||
        (sport?.name ?? "").toLowerCase().includes(search);
      const matchesVenue = !courtVenueFilter || court.venue_id === courtVenueFilter;
      const matchesSport = !courtSportFilter || court.sport_id === courtSportFilter;
      const matchesStatus =
        courtStatusFilter === "all" ||
        (courtStatusFilter === "active" && court.is_active) ||
        (courtStatusFilter === "inactive" && !court.is_active);

      return matchesSearch && matchesVenue && matchesSport && matchesStatus;
    });
  }, [courtSearch, courtSportFilter, courtStatusFilter, courtVenueFilter, courtsQuery.data, sportsById, venuesById]);

  function invalidateInventoryQueries() {
    void queryClient.invalidateQueries({ queryKey: ["venues"] });
    void queryClient.invalidateQueries({ queryKey: ["courts"] });
    void queryClient.invalidateQueries({ queryKey: ["timeslots"] });
  }

  const createVenueMutation = useMutation({
    mutationFn: api.createVenue,
    onSuccess: () => {
      setVenueError(null);
      setVenueSuccess("Sede creada correctamente.");
      setVenueName("");
      setVenueAddress("");
      setVenueTimezone(DEFAULT_TIMEZONE);
      setVenueAllowedSportId("");
      invalidateInventoryQueries();
    },
    onError: (error) => {
      setVenueSuccess(null);
      setVenueError(error instanceof Error ? error.message : "No pudimos crear la sede.");
    },
  });

  const updateVenueMutation = useMutation({
    mutationFn: ({ venueId, payload }: { venueId: string; payload: Parameters<typeof api.updateVenue>[1] }) =>
      api.updateVenue(venueId, payload),
    onSuccess: () => {
      setVenueError(null);
      setVenueSuccess("Sede actualizada correctamente.");
      setEditingVenueId(null);
      invalidateInventoryQueries();
    },
    onError: (error) => {
      setVenueSuccess(null);
      setVenueError(error instanceof Error ? error.message : "No pudimos actualizar la sede.");
    },
  });

  const deleteVenueMutation = useMutation({
    mutationFn: api.deleteVenue,
    onSuccess: () => {
      setVenueError(null);
      setVenueSuccess("Sede eliminada correctamente.");
      invalidateInventoryQueries();
    },
    onError: (error) => {
      setVenueSuccess(null);
      setVenueError(error instanceof Error ? error.message : "No pudimos eliminar la sede.");
    },
  });

  const createCourtMutation = useMutation({
    mutationFn: api.createCourt,
    onSuccess: () => {
      setCourtError(null);
      setCourtSuccess("Cancha creada correctamente.");
      setCourtName("");
      setCourtVenueId("");
      setCourtSportId("");
      setCourtIndoor("indoor");
      setCourtIsActive(true);
      invalidateInventoryQueries();
    },
    onError: (error) => {
      setCourtSuccess(null);
      setCourtError(error instanceof Error ? error.message : "No pudimos crear la cancha.");
    },
  });

  const updateCourtMutation = useMutation({
    mutationFn: ({ courtId, payload }: { courtId: string; payload: Parameters<typeof api.updateCourt>[1] }) =>
      api.updateCourt(courtId, payload),
    onSuccess: () => {
      setCourtError(null);
      setCourtSuccess("Cancha actualizada correctamente.");
      setEditingCourtId(null);
      invalidateInventoryQueries();
    },
    onError: (error) => {
      setCourtSuccess(null);
      setCourtError(error instanceof Error ? error.message : "No pudimos actualizar la cancha.");
    },
  });

  const deleteCourtMutation = useMutation({
    mutationFn: api.deleteCourt,
    onSuccess: () => {
      setCourtError(null);
      setCourtSuccess("Cancha eliminada correctamente.");
      invalidateInventoryQueries();
    },
    onError: (error) => {
      setCourtSuccess(null);
      setCourtError(error instanceof Error ? error.message : "No pudimos eliminar la cancha.");
    },
  });
  function handleCreateVenue(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setVenueError(null);
    setVenueSuccess(null);

    if (!venueName.trim()) {
      setVenueError("La sede necesita un nombre.");
      return;
    }

    createVenueMutation.mutate({
      name: venueName.trim(),
      address: normalizeOptionalText(venueAddress),
      timezone: venueTimezone.trim() || DEFAULT_TIMEZONE,
      allowed_sport_id: venueAllowedSportId || null,
    });
  }

  function handleCreateCourt(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCourtError(null);
    setCourtSuccess(null);

    if (!courtName.trim() || !courtVenueId || !courtSportId) {
      setCourtError("Completá nombre, sede y deporte para crear la cancha.");
      return;
    }

    createCourtMutation.mutate({
      name: courtName.trim(),
      venue_id: courtVenueId,
      sport_id: courtSportId,
      indoor: courtIndoor === "indoor",
      is_active: courtIsActive,
    });
  }

  function startVenueEdit(venue: Venue) {
    setEditingVenueId(venue.id);
    setEditVenueName(venue.name);
    setEditVenueAddress(venue.address ?? "");
    setEditVenueTimezone(venue.timezone);
    setEditVenueAllowedSportId(venue.allowed_sport_id ?? "");
    setVenueError(null);
    setVenueSuccess(null);
  }

  function startCourtEdit(court: Court) {
    setEditingCourtId(court.id);
    setEditCourtName(court.name);
    setEditCourtVenueId(court.venue_id);
    setEditCourtSportId(court.sport_id);
    setEditCourtIndoor(court.indoor === false ? "outdoor" : "indoor");
    setEditCourtIsActive(court.is_active);
    setCourtError(null);
    setCourtSuccess(null);
  }

  function handleUpdateVenue(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editingVenueId) {
      return;
    }

    if (!editVenueName.trim()) {
      setVenueError("La sede necesita un nombre.");
      return;
    }

    updateVenueMutation.mutate({
      venueId: editingVenueId,
      payload: {
        name: editVenueName.trim(),
        address: normalizeOptionalText(editVenueAddress),
        timezone: editVenueTimezone.trim() || DEFAULT_TIMEZONE,
        allowed_sport_id: editVenueAllowedSportId || null,
      },
    });
  }

  function handleUpdateCourt(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editingCourtId) {
      return;
    }

    if (!editCourtName.trim() || !editCourtVenueId || !editCourtSportId) {
      setCourtError("Completá nombre, sede y deporte para guardar la cancha.");
      return;
    }

    updateCourtMutation.mutate({
      courtId: editingCourtId,
      payload: {
        name: editCourtName.trim(),
        venue_id: editCourtVenueId,
        sport_id: editCourtSportId,
        indoor: editCourtIndoor === "indoor",
        is_active: editCourtIsActive,
      },
    });
  }

  async function handleDeleteVenue(venue: Venue) {
    const confirmed = await confirmDestructiveAction({
      title: "Eliminar sede",
      text: `Vas a eliminar ${venue.name}. Esta acción no se puede deshacer.`,
      confirmText: "Sí, eliminar",
    });
    if (!confirmed) {
      return;
    }
    setVenueError(null);
    setVenueSuccess(null);
    deleteVenueMutation.mutate(venue.id);
  }

  async function handleDeleteCourt(court: Court) {
    const confirmed = await confirmDestructiveAction({
      title: "Eliminar cancha",
      text: `Vas a eliminar ${court.name}. Esta acción no se puede deshacer.`,
      confirmText: "Sí, eliminar",
    });
    if (!confirmed) {
      return;
    }
    setCourtError(null);
    setCourtSuccess(null);
    deleteCourtMutation.mutate(court.id);
  }

  const inventoryLoading = sportsQuery.isLoading || venuesQuery.isLoading || courtsQuery.isLoading;

  return (
    <>
      <AppHeader />
      <section className="space-y-6">
        <SectionTitle
          eyebrow="Admin"
          title="Gestión de sedes, canchas y políticas"
          description="Cargá la estructura base del complejo, organizá qué deporte aplica en cada sede y definí ventanas de reserva y cancelación más claras para cada disciplina."
        />

        <AdminNav />

        <div className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
          <div className="space-y-4">
            <form className="shell-card space-y-4 p-5" onSubmit={handleCreateVenue}>
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-sky-100 text-sky-700">
                  <Building2 size={18} />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-slate-950">Nueva sede</h3>
                  <p className="text-sm text-slate-500">Definí nombre, dirección y si la sede limita el deporte disponible.</p>
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="sm:col-span-2">
                  <label className="mb-2 block text-sm font-semibold text-slate-700" htmlFor="venue-name">
                    Nombre
                  </label>
                  <input id="venue-name" className="field" value={venueName} onChange={(event) => setVenueName(event.target.value)} placeholder="Ej. Sede Centro" />
                </div>

                <div className="sm:col-span-2">
                  <label className="mb-2 block text-sm font-semibold text-slate-700" htmlFor="venue-address">
                    Dirección
                  </label>
                  <input id="venue-address" className="field" value={venueAddress} onChange={(event) => setVenueAddress(event.target.value)} placeholder="Opcional" />
                </div>

                <div>
                  <label className="mb-2 block text-sm font-semibold text-slate-700" htmlFor="venue-timezone">
                    Zona horaria
                  </label>
                  <input id="venue-timezone" className="field" value={venueTimezone} onChange={(event) => setVenueTimezone(event.target.value)} />
                </div>

                <div>
                  <label className="mb-2 block text-sm font-semibold text-slate-700" htmlFor="venue-sport">
                    Deporte permitido
                  </label>
                  <select id="venue-sport" className="field" value={venueAllowedSportId} onChange={(event) => setVenueAllowedSportId(event.target.value)}>
                    <option value="">Todos los deportes</option>
                    {(sportsQuery.data ?? []).map((sport) => (
                      <option key={sport.id} value={sport.id}>
                        {sport.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {venueError ? <Feedback tone="error" message={venueError} /> : null}
              {venueSuccess ? <Feedback tone="success" message={venueSuccess} /> : null}

              <button className="btn-primary w-full" type="submit" disabled={createVenueMutation.isPending}>
                {createVenueMutation.isPending ? (
                  <span className="inline-flex items-center gap-2">
                    <LoaderCircle className="animate-spin" size={16} />
                    Creando sede...
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-2">
                    <Plus size={16} />
                    Crear sede
                  </span>
                )}
              </button>
            </form>

            <form className="shell-card space-y-4 p-5" onSubmit={handleCreateCourt}>
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-orange-100 text-orange-700">
                  <Volleyball size={18} />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-slate-950">Nueva cancha</h3>
                  <p className="text-sm text-slate-500">Asigná la cancha a una sede, elegí deporte y dejala activa para reservas.</p>
                </div>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="sm:col-span-2">
                  <label className="mb-2 block text-sm font-semibold text-slate-700" htmlFor="court-name">
                    Nombre
                  </label>
                  <input id="court-name" className="field" value={courtName} onChange={(event) => setCourtName(event.target.value)} placeholder="Ej. Cancha 1" />
                </div>

                <div>
                  <label className="mb-2 block text-sm font-semibold text-slate-700" htmlFor="court-venue">
                    Sede
                  </label>
                  <select
                    id="court-venue"
                    className="field"
                    value={courtVenueId}
                    onChange={(event) => {
                      const nextVenueId = event.target.value;
                      setCourtVenueId(nextVenueId);
                      const selectedVenue = nextVenueId ? venuesById.get(nextVenueId) ?? null : null;
                      if (selectedVenue?.allowed_sport_id) {
                        setCourtSportId(selectedVenue.allowed_sport_id);
                      }
                    }}
                  >
                    <option value="">Seleccionar sede</option>
                    {(venuesQuery.data ?? []).map((venue) => (
                      <option key={venue.id} value={venue.id}>
                        {venue.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="mb-2 block text-sm font-semibold text-slate-700" htmlFor="court-sport">
                    Deporte
                  </label>
                  <select id="court-sport" className="field" value={courtSportId} onChange={(event) => setCourtSportId(event.target.value)}>
                    <option value="">Seleccionar deporte</option>
                    {availableSportsForCourt.map((sport) => (
                      <option key={sport.id} value={sport.id}>
                        {sport.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="mb-2 block text-sm font-semibold text-slate-700" htmlFor="court-type">
                    Tipo
                  </label>
                  <select id="court-type" className="field" value={courtIndoor} onChange={(event) => setCourtIndoor(event.target.value)}>
                    <option value="indoor">Indoor</option>
                    <option value="outdoor">Outdoor</option>
                  </select>
                </div>

                <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                  <input type="checkbox" checked={courtIsActive} onChange={(event) => setCourtIsActive(event.target.checked)} />
                  Dejar la cancha activa
                </label>
              </div>

              {courtError ? <Feedback tone="error" message={courtError} /> : null}
              {courtSuccess ? <Feedback tone="success" message={courtSuccess} /> : null}

              <button className="btn-primary w-full" type="submit" disabled={createCourtMutation.isPending}>
                {createCourtMutation.isPending ? (
                  <span className="inline-flex items-center gap-2">
                    <LoaderCircle className="animate-spin" size={16} />
                    Creando cancha...
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-2">
                    <Plus size={16} />
                    Crear cancha
                  </span>
                )}
              </button>
            </form>
          </div>

          <div className="space-y-4">
            <AdminSportPolicies />

            <div className="shell-card p-5">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-100 text-slate-700">
                  <MapPinned size={18} />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-slate-950">Sedes cargadas</h3>
                  <p className="text-sm text-slate-500">Editalas inline o eliminá las que todavía no tengan canchas asociadas.</p>
                </div>
              </div>

              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <input
                  className="field sm:col-span-2"
                  value={venueSearch}
                  onChange={(event) => setVenueSearch(event.target.value)}
                  placeholder="Buscar por nombre o dirección"
                />
                <select className="field" value={venueSportFilter} onChange={(event) => setVenueSportFilter(event.target.value)}>
                  <option value="">Todos los deportes</option>
                  {(sportsQuery.data ?? []).map((sport) => (
                    <option key={sport.id} value={sport.id}>
                      {sport.name}
                    </option>
                  ))}
                </select>
                <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-500">
                  {filteredVenues.length} sedes visibles
                </div>
              </div>

              {inventoryLoading ? (
                <div className="mt-4">
                  <LoadingCard label="Cargando inventario..." />
                </div>
              ) : filteredVenues.length ? (
                <div className="mt-4 space-y-3">
                  {filteredVenues.map((venue) => {
                    const isEditing = editingVenueId === venue.id;
                    const sportName = venue.allowed_sport_id ? sportsById.get(venue.allowed_sport_id)?.name ?? "Deporte" : "Todos los deportes";
                    const attachedCourts = (courtsQuery.data ?? []).filter((court) => court.venue_id === venue.id).length;

                    return (
                      <article key={venue.id} className="rounded-3xl border border-slate-200 bg-white p-4">
                        {!isEditing ? (
                          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                            <div>
                              <p className="text-lg font-bold text-slate-950">{venue.name}</p>
                              <p className="mt-1 text-sm text-slate-500">{venue.address || "Sin dirección cargada"}</p>
                              <div className="mt-3 flex flex-wrap gap-2 text-xs font-semibold">
                                <span className="rounded-full bg-slate-100 px-3 py-1 text-slate-600">{sportName}</span>
                                <span className="rounded-full bg-slate-100 px-3 py-1 text-slate-600">{venue.timezone}</span>
                                <span className="rounded-full bg-slate-100 px-3 py-1 text-slate-600">{attachedCourts} canchas</span>
                              </div>
                            </div>

                            <div className="flex flex-wrap gap-2">
                              <button className="btn-secondary" type="button" onClick={() => startVenueEdit(venue)}>
                                <PencilLine size={16} />
                                Editar
                              </button>
                              <button className="btn-secondary text-rose-700" type="button" onClick={() => handleDeleteVenue(venue)} disabled={deleteVenueMutation.isPending}>
                                <Trash2 size={16} />
                                Eliminar
                              </button>
                            </div>
                          </div>
                        ) : (
                          <form className="grid gap-4" onSubmit={handleUpdateVenue}>
                            <div className="grid gap-4 sm:grid-cols-2">
                              <input className="field sm:col-span-2" value={editVenueName} onChange={(event) => setEditVenueName(event.target.value)} placeholder="Nombre de la sede" />
                              <input className="field sm:col-span-2" value={editVenueAddress} onChange={(event) => setEditVenueAddress(event.target.value)} placeholder="Dirección" />
                              <input className="field" value={editVenueTimezone} onChange={(event) => setEditVenueTimezone(event.target.value)} placeholder="Zona horaria" />
                              <select className="field" value={editVenueAllowedSportId} onChange={(event) => setEditVenueAllowedSportId(event.target.value)}>
                                <option value="">Todos los deportes</option>
                                {(sportsQuery.data ?? []).map((sport) => (
                                  <option key={sport.id} value={sport.id}>
                                    {sport.name}
                                  </option>
                                ))}
                              </select>
                            </div>

                            <div className="flex flex-wrap gap-2">
                              <button className="btn-primary" type="submit" disabled={updateVenueMutation.isPending}>
                                {updateVenueMutation.isPending ? (
                                  <span className="inline-flex items-center gap-2">
                                    <LoaderCircle className="animate-spin" size={16} />
                                    Guardando...
                                  </span>
                                ) : (
                                  <span className="inline-flex items-center gap-2">
                                    <Save size={16} />
                                    Guardar sede
                                  </span>
                                )}
                              </button>
                              <button className="btn-secondary" type="button" onClick={() => setEditingVenueId(null)}>
                                Cancelar
                              </button>
                            </div>
                          </form>
                        )}
                      </article>
                    );
                  })}
                </div>
              ) : (
                <div className="mt-4">
                  <EmptyState title="Todavía no hay sedes" description="Creá la primera sede para empezar a organizar las canchas del complejo." />
                </div>
              )}
            </div>

            <div className="shell-card p-5">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-700">
                  <Shield size={18} />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-slate-950">Canchas cargadas</h3>
                  <p className="text-sm text-slate-500">Podés moverlas de sede, cambiar deporte o desactivarlas sin salir de la vista.</p>
                </div>
              </div>

              <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <input
                  className="field sm:col-span-2 xl:col-span-4"
                  value={courtSearch}
                  onChange={(event) => setCourtSearch(event.target.value)}
                  placeholder="Buscar por cancha, sede o deporte"
                />
                <select className="field" value={courtVenueFilter} onChange={(event) => setCourtVenueFilter(event.target.value)}>
                  <option value="">Todas las sedes</option>
                  {(venuesQuery.data ?? []).map((venue) => (
                    <option key={venue.id} value={venue.id}>
                      {venue.name}
                    </option>
                  ))}
                </select>
                <select className="field" value={courtSportFilter} onChange={(event) => setCourtSportFilter(event.target.value)}>
                  <option value="">Todos los deportes</option>
                  {(sportsQuery.data ?? []).map((sport) => (
                    <option key={sport.id} value={sport.id}>
                      {sport.name}
                    </option>
                  ))}
                </select>
                <select className="field" value={courtStatusFilter} onChange={(event) => setCourtStatusFilter(event.target.value)}>
                  <option value="all">Activas e inactivas</option>
                  <option value="active">Solo activas</option>
                  <option value="inactive">Solo inactivas</option>
                </select>
                <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-500">
                  {filteredCourts.length} canchas visibles
                </div>
              </div>

              {inventoryLoading ? (
                <div className="mt-4">
                  <LoadingCard label="Cargando canchas..." />
                </div>
              ) : filteredCourts.length ? (
                <div className="mt-4 space-y-3">
                  {filteredCourts.map((court) => {
                    const isEditing = editingCourtId === court.id;
                    const venue = venuesById.get(court.venue_id);
                    const sport = sportsById.get(court.sport_id);

                    return (
                      <article key={court.id} className="rounded-3xl border border-slate-200 bg-white p-4">
                        {!isEditing ? (
                          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                            <div>
                              <p className="text-lg font-bold text-slate-950">{court.name}</p>
                              <div className="mt-2 flex flex-wrap gap-2 text-xs font-semibold">
                                <span className="rounded-full bg-slate-100 px-3 py-1 text-slate-600">{venue?.name || "Sede"}</span>
                                <span className="rounded-full bg-slate-100 px-3 py-1 text-slate-600">{sport?.name || "Deporte"}</span>
                                <span className="rounded-full bg-slate-100 px-3 py-1 text-slate-600">{court.indoor ? "Indoor" : "Outdoor"}</span>
                                <span className={`rounded-full px-3 py-1 ${court.is_active ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-500"}`}>
                                  {court.is_active ? "Activa" : "Inactiva"}
                                </span>
                              </div>
                            </div>

                            <div className="flex flex-wrap gap-2">
                              <button className="btn-secondary" type="button" onClick={() => startCourtEdit(court)}>
                                <PencilLine size={16} />
                                Editar
                              </button>
                              <button className="btn-secondary text-rose-700" type="button" onClick={() => handleDeleteCourt(court)} disabled={deleteCourtMutation.isPending}>
                                <Trash2 size={16} />
                                Eliminar
                              </button>
                            </div>
                          </div>
                        ) : (
                          <form className="grid gap-4" onSubmit={handleUpdateCourt}>
                            <div className="grid gap-4 sm:grid-cols-2">
                              <input className="field sm:col-span-2" value={editCourtName} onChange={(event) => setEditCourtName(event.target.value)} placeholder="Nombre de la cancha" />
                              <select
                                className="field"
                                value={editCourtVenueId}
                                onChange={(event) => {
                                  const nextVenueId = event.target.value;
                                  setEditCourtVenueId(nextVenueId);
                                  const selectedVenue = nextVenueId ? venuesById.get(nextVenueId) ?? null : null;
                                  if (selectedVenue?.allowed_sport_id) {
                                    setEditCourtSportId(selectedVenue.allowed_sport_id);
                                  }
                                }}
                              >
                                <option value="">Seleccionar sede</option>
                                {(venuesQuery.data ?? []).map((venueOption) => (
                                  <option key={venueOption.id} value={venueOption.id}>
                                    {venueOption.name}
                                  </option>
                                ))}
                              </select>
                              <select className="field" value={editCourtSportId} onChange={(event) => setEditCourtSportId(event.target.value)}>
                                <option value="">Seleccionar deporte</option>
                                {availableEditSportsForCourt.map((sportOption) => (
                                  <option key={sportOption.id} value={sportOption.id}>
                                    {sportOption.name}
                                  </option>
                                ))}
                              </select>
                              <select className="field" value={editCourtIndoor} onChange={(event) => setEditCourtIndoor(event.target.value)}>
                                <option value="indoor">Indoor</option>
                                <option value="outdoor">Outdoor</option>
                              </select>
                              <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                                <input type="checkbox" checked={editCourtIsActive} onChange={(event) => setEditCourtIsActive(event.target.checked)} />
                                Cancha activa
                              </label>
                            </div>

                            <div className="flex flex-wrap gap-2">
                              <button className="btn-primary" type="submit" disabled={updateCourtMutation.isPending}>
                                {updateCourtMutation.isPending ? (
                                  <span className="inline-flex items-center gap-2">
                                    <LoaderCircle className="animate-spin" size={16} />
                                    Guardando...
                                  </span>
                                ) : (
                                  <span className="inline-flex items-center gap-2">
                                    <Save size={16} />
                                    Guardar cancha
                                  </span>
                                )}
                              </button>
                              <button className="btn-secondary" type="button" onClick={() => setEditingCourtId(null)}>
                                Cancelar
                              </button>
                            </div>
                          </form>
                        )}
                      </article>
                    );
                  })}
                </div>
              ) : (
                <div className="mt-4">
                  <EmptyState title="Todavía no hay canchas" description="Creá una cancha y asignala a una sede para seguir con la carga operativa." />
                </div>
              )}
            </div>
          </div>
        </div>
      </section>
    </>
  );
}

function Feedback({ tone, message }: { tone: "error" | "success"; message: string }) {
  return (
    <div
      className={`rounded-2xl border px-4 py-3 text-sm ${
        tone === "error"
          ? "border-rose-200 bg-rose-50 text-rose-700"
          : "border-emerald-200 bg-emerald-50 text-emerald-700"
      }`}
    >
      <div className="flex items-start gap-2">
        {tone === "error" ? <CircleAlert className="mt-0.5" size={16} /> : <Save className="mt-0.5" size={16} />}
        <span>{message}</span>
      </div>
    </div>
  );
}




