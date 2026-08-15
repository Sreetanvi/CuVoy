"use client";

import type { Session, User } from "@supabase/supabase-js";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  authCallbackUrl,
  consumeAuthResume,
  type AuthIntent,
  writeAuthResume,
} from "@/lib/auth";
import { getSupabaseBrowserClient } from "@/lib/supabase";

type AuthContextValue = {
  user: User | null;
  session: Session | null;
  loading: boolean;
  configured: boolean;
  accessToken: string | null;
  modalOpen: boolean;
  modalIntent: AuthIntent;
  openAuth: (intent?: AuthIntent) => void;
  closeAuth: () => void;
  signInWithGoogle: () => Promise<void>;
  signInWithEmail: (email: string, password: string) => Promise<void>;
  signUpWithEmail: (email: string, password: string) => Promise<{ needsConfirm: boolean }>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const configured = Boolean(getSupabaseBrowserClient());
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalIntent, setModalIntent] = useState<AuthIntent>("login");

  useEffect(() => {
    const supabase = getSupabaseBrowserClient();
    if (!supabase) {
      setLoading(false);
      return;
    }

    void supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setUser(data.session?.user ?? null);
      setLoading(false);
    });

    const { data } = supabase.auth.onAuthStateChange((_event, next) => {
      setSession(next);
      setUser(next?.user ?? null);
    });
    return () => data.subscription.unsubscribe();
  }, []);

  const openAuth = useCallback((intent: AuthIntent = "login") => {
    setModalIntent(intent);
    setModalOpen(true);
  }, []);

  const closeAuth = useCallback(() => {
    setModalOpen(false);
  }, []);

  useEffect(() => {
    if (loading || !user) {
      return;
    }
    const resume = consumeAuthResume();
    if (resume?.intent === "save" || resume?.intent === "share") {
      openAuth(resume.intent);
    }
  }, [loading, openAuth, user]);

  const signInWithGoogle = useCallback(async () => {
    const supabase = getSupabaseBrowserClient();
    if (!supabase) {
      throw new Error("Supabase Auth is not configured.");
    }
    writeAuthResume({
      intent: modalIntent,
      returnTo: `${window.location.pathname}${window.location.search}`,
    });
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: authCallbackUrl() },
    });
    if (error) {
      throw error;
    }
  }, [modalIntent]);

  const signInWithEmail = useCallback(async (email: string, password: string) => {
    const supabase = getSupabaseBrowserClient();
    if (!supabase) {
      throw new Error("Supabase Auth is not configured.");
    }
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) {
      throw error;
    }
  }, []);

  const signUpWithEmail = useCallback(async (email: string, password: string) => {
    const supabase = getSupabaseBrowserClient();
    if (!supabase) {
      throw new Error("Supabase Auth is not configured.");
    }
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: { emailRedirectTo: authCallbackUrl() },
    });
    if (error) {
      throw error;
    }
    return { needsConfirm: !data.session };
  }, []);

  const signOut = useCallback(async () => {
    const supabase = getSupabaseBrowserClient();
    if (!supabase) {
      return;
    }
    await supabase.auth.signOut();
  }, []);

  const value = useMemo(
    () => ({
      user,
      session,
      loading,
      configured,
      accessToken: session?.access_token ?? null,
      modalOpen,
      modalIntent,
      openAuth,
      closeAuth,
      signInWithGoogle,
      signInWithEmail,
      signUpWithEmail,
      signOut,
    }),
    [
      closeAuth,
      configured,
      loading,
      modalIntent,
      modalOpen,
      openAuth,
      session,
      signInWithEmail,
      signInWithGoogle,
      signOut,
      signUpWithEmail,
      user,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return value;
}
