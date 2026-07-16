import type { ReactNode } from "react";
import type { Role } from "../types/auth";
import { useAuth } from "./AuthContext";

export function RoleGate({ allow, children }: { allow: Role[]; children: ReactNode }) {
  const { role } = useAuth();
  if (!role || !allow.includes(role)) {
    return null;
  }
  return <>{children}</>;
}
