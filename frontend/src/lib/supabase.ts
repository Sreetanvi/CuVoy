import { createClient, type SupabaseClient } from "@supabase/supabase-js";

let browserClient: SupabaseClient | null | undefined;

export function getSupabaseBrowserClient(): SupabaseClient | null {
  if (browserClient !== undefined) {
    return browserClient;
  }

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL?.trim();
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY?.trim();
  if (!url || !anonKey) {
    browserClient = null;
    return browserClient;
  }

  browserClient = createClient(url, anonKey, {
    auth: {
      persistSession: true,
      detectSessionInUrl: true,
    },
  });
  return browserClient;
}
