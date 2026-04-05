import {
  createContext,
  startTransition,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { api, type User } from "../../lib/api";
import { clearTokens, getStoredTokens, storeTokens } from "../../lib/storage";

type AuthContextValue = {
  user: User | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  isStaff: boolean;
  canAccessAdmin: boolean;
  canManageOrganization: boolean;
  canManageStaff: boolean;
  canViewMetrics: boolean;
  canManageInventory: boolean;
  canManageTimeslots: boolean;
  canManageWhatsapp: boolean;
  loading: boolean;
  login: (input: { email: string; password: string }) => Promise<void>;
  register: (input: { email: string; password: string; full_name: string; whatsapp_number?: string | null; whatsapp_opt_in?: boolean }) => Promise<void>;
  onboardOrganization: (input: {
    organization_name: string;
    organization_slug?: string | null;
    admin_full_name: string;
    admin_email: string;
    admin_password: string;
    whatsapp_number?: string | null;
    whatsapp_opt_in?: boolean;
  }) => Promise<void>;
  acceptStaffInvitation: (input: {
    token: string;
    full_name?: string | null;
    password: string;
    whatsapp_number?: string | null;
    whatsapp_opt_in?: boolean;
  }) => Promise<void>;
  updateProfile: (input: { full_name?: string | null; whatsapp_number?: string | null; whatsapp_opt_in?: boolean }) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const tokens = getStoredTokens();

    if (!tokens) {
      setLoading(false);
      return;
    }

    void api
      .me()
      .then((currentUser) => {
        startTransition(() => {
          setUser(currentUser);
        });
      })
      .catch(() => {
        clearTokens();
        setUser(null);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  async function login(input: { email: string; password: string }) {
    const tokens = await api.login(input);
    storeTokens({
      accessToken: tokens.access_token,
      refreshToken: tokens.refresh_token,
    });
    const currentUser = await api.me();
    setUser(currentUser);
  }

  async function register(input: { email: string; password: string; full_name: string; whatsapp_number?: string | null; whatsapp_opt_in?: boolean }) {
    await api.register(input);
    await login({ email: input.email, password: input.password });
  }

  async function onboardOrganization(input: {
    organization_name: string;
    organization_slug?: string | null;
    admin_full_name: string;
    admin_email: string;
    admin_password: string;
    whatsapp_number?: string | null;
    whatsapp_opt_in?: boolean;
  }) {
    const result = await api.onboardOrganization(input);
    storeTokens({
      accessToken: result.access_token,
      refreshToken: result.refresh_token,
    });
    const currentUser = await api.me();
    setUser(currentUser);
  }

  async function acceptStaffInvitation(input: {
    token: string;
    full_name?: string | null;
    password: string;
    whatsapp_number?: string | null;
    whatsapp_opt_in?: boolean;
  }) {
    const result = await api.acceptStaffInvitation(input);
    storeTokens({
      accessToken: result.access_token,
      refreshToken: result.refresh_token,
    });
    const currentUser = await api.me();
    setUser(currentUser);
  }

  async function updateProfile(input: { full_name?: string | null; whatsapp_number?: string | null; whatsapp_opt_in?: boolean }) {
    const currentUser = await api.updateMe(input);
    setUser(currentUser);
  }

  function logout() {
    clearTokens();
    setUser(null);
  }

  const permissions = user?.permissions;

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: Boolean(user),
        isAdmin: user?.role === "admin",
        isStaff: user?.role === "staff",
        canAccessAdmin: Boolean(
          permissions?.manage_organization ||
            permissions?.manage_staff ||
            permissions?.view_metrics ||
            permissions?.manage_inventory ||
            permissions?.manage_timeslots ||
            permissions?.manage_whatsapp,
        ),
        canManageOrganization: Boolean(permissions?.manage_organization),
        canManageStaff: Boolean(permissions?.manage_staff),
        canViewMetrics: Boolean(permissions?.view_metrics),
        canManageInventory: Boolean(permissions?.manage_inventory),
        canManageTimeslots: Boolean(permissions?.manage_timeslots),
        canManageWhatsapp: Boolean(permissions?.manage_whatsapp),
        loading,
        login,
        register,
        onboardOrganization,
        acceptStaffInvitation,
        updateProfile,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth debe usarse dentro de AuthProvider");
  }

  return context;
}
