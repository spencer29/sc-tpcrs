import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import { login as apiLogin, verifyMfa as apiVerifyMfa } from "../api/auth";
import { setAccessToken as setClientAccessToken } from "../api/client";
import type { Role } from "../types/auth";

interface AuthContextValue {
  role: Role | null;
  sub: string | null;
  isAuthenticated: boolean;
  loginStep1: (email: string, password: string) => Promise<string>;
  loginStep2: (mfaBridgeToken: string, otpCode: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [role, setRole] = useState<Role | null>(null);
  const [sub, setSub] = useState<string | null>(null);

  const loginStep1 = useCallback(async (email: string, password: string): Promise<string> => {
    const result = await apiLogin(email, password);
    return result.mfa_bridge_token;
  }, []);

  const loginStep2 = useCallback(async (mfaBridgeToken: string, otpCode: string): Promise<void> => {
    const result = await apiVerifyMfa(mfaBridgeToken, otpCode);
    setClientAccessToken(result.access_token);
    setRole(result.role as Role);
    setSub(result.sub);
  }, []);

  const logout = useCallback(() => {
    setClientAccessToken(null);
    setRole(null);
    setSub(null);
  }, []);

  return (
    <AuthContext.Provider value={{ role, sub, isAuthenticated: sub !== null, loginStep1, loginStep2, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
