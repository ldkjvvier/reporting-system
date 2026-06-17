import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { auth, getToken } from "./api";
import type { User } from "./types";

interface AuthCtx {
  user: User | null;
  isAuthed: boolean;
  isAdmin: boolean;
  loading: boolean;
  /** true si el usuario es admin o editor del equipo indicado. */
  canEdit: (teamId: number) => boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const Ctx = createContext<AuthCtx>(null as unknown as AuthCtx);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [authed, setAuthed] = useState<boolean>(!!getToken());
  const [loading, setLoading] = useState<boolean>(!!getToken());

  // Tras refrescar la página el token sigue en localStorage pero perdemos al
  // usuario en memoria: lo rehidratamos con /api/auth/me.
  useEffect(() => {
    if (getToken() && !user) {
      auth
        .me()
        .then(setUser)
        .catch(() => {
          auth.logout();
          setAuthed(false);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (email: string, password: string) => {
    const u = await auth.login(email, password);
    setUser(u);
    setAuthed(true);
  };

  const logout = () => {
    auth.logout();
    setUser(null);
    setAuthed(false);
  };

  const canEdit = (teamId: number) => {
    if (!user) return false;
    if (user.is_admin) return true;
    return user.memberships.some(
      (m) => m.team_id === teamId && m.role === "editor"
    );
  };

  return (
    <Ctx.Provider
      value={{
        user,
        isAuthed: authed,
        isAdmin: !!user?.is_admin,
        loading,
        canEdit,
        login,
        logout,
      }}
    >
      {children}
    </Ctx.Provider>
  );
}

export const useAuth = () => useContext(Ctx);
