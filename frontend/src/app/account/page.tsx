import type { Metadata } from "next";

import { AccountSettings } from "@/components/auth/AccountSettings";
import { PageFrame } from "@/components/layout/PageFrame";

export const metadata: Metadata = {
  title: "Account — CuVoy",
  robots: { index: false, follow: false },
};

export default function AccountPage() {
  return (
    <PageFrame>
      <AccountSettings />
    </PageFrame>
  );
}
