import { apiRequest } from "./client";

export interface LoginResponse {
  mfa_bridge_token: string;
  expires_in: number;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  role: string;
  sub: string;
  expires_in: number;
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  return apiRequest<LoginResponse>("/auth/login", { method: "POST", body: { email, password } });
}

export async function verifyMfa(mfaBridgeToken: string, otpCode: string): Promise<TokenResponse> {
  return apiRequest<TokenResponse>("/auth/mfa/verify", {
    method: "POST",
    body: { mfa_bridge_token: mfaBridgeToken, otp_code: otpCode },
  });
}
