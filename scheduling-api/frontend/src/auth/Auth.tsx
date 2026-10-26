import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { api, json, onExpired, setToken } from "../api/client";
import type { User } from "../types";
const Context = createContext<{
  user: User | null;
  reason: string;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
} | null>(null);
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [reason, setReason] = useState("");
  const logout = () => {
    setToken(null);
    setUser(null);
    setReason("");
  };
  useEffect(
    () =>
      onExpired(() => {
        setUser(null);
        setReason("Sua sessão expirou. Entre novamente.");
      }),
    [],
  );
  async function login(email: string, password: string) {
    const result = await api<{ access_token: string }>(
      "/auth/login",
      json("POST", { email, password }),
      false,
    );
    setToken(result.access_token);
    try {
      setUser(await api<User>("/users/me"));
      setReason("");
    } catch (error) {
      logout();
      throw error;
    }
  }
  return (
    <Context.Provider value={{ user, reason, login, logout }}>
      {children}
    </Context.Provider>
  );
}
export function useAuth() {
  const value = useContext(Context);
  if (!value) throw new Error("AuthProvider ausente");
  return value;
}
