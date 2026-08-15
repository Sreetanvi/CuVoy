import { getSupabaseBrowserClient } from "@/lib/supabase";

export const AUTH_RESUME_KEY = "cuvoy.auth.resume";

export type AuthIntent = "login" | "save" | "share";

export type AuthResume = {
  intent: AuthIntent;
  planId?: string;
  returnTo?: string;
};

export async function getAccessToken(): Promise<string | null> {
  const supabase = getSupabaseBrowserClient();
  if (!supabase) {
    return null;
  }
  const { data } = await supabase.auth.getSession();
  if (data.session?.access_token) {
    return data.session.access_token;
  }
  const { data: refreshed } = await supabase.auth.refreshSession();
  return refreshed.session?.access_token ?? null;
}

export function writeAuthResume(resume: AuthResume): void {
  try {
    sessionStorage.setItem(AUTH_RESUME_KEY, JSON.stringify(resume));
  } catch {
    /* private mode */
  }
}

export function readAuthResume(): AuthResume | null {
  try {
    const raw = sessionStorage.getItem(AUTH_RESUME_KEY);
    if (!raw) {
      return null;
    }
    return JSON.parse(raw) as AuthResume;
  } catch {
    return null;
  }
}

export function consumeAuthResume(): AuthResume | null {
  const resume = readAuthResume();
  try {
    sessionStorage.removeItem(AUTH_RESUME_KEY);
  } catch {
    /* ignore */
  }
  return resume;
}

export function authCallbackUrl(): string {
  return `${window.location.origin}/auth/callback`;
}
