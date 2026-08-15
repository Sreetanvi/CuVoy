import type { Metadata } from "next";

import { AuthCallbackClient } from "@/components/auth/AuthCallbackClient";

export const metadata: Metadata = {
  title: "Signing in — CuVoy",
  robots: { index: false, follow: false },
};

export default function AuthCallbackPage() {
  return <AuthCallbackClient />;
}
