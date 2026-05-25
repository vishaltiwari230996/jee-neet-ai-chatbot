import { SignUp } from "@clerk/nextjs";
import Link from "next/link";

export default function SignUpPage() {
  return (
    <main className="flex min-h-dvh flex-col items-center justify-center px-5 py-12">
      <Link
        href="/"
        className="mb-6 text-sm text-[var(--color-fg-muted)] hover:text-[var(--color-fg)]"
      >
        ← Home
      </Link>
      <SignUp signInUrl="/sign-in" />
    </main>
  );
}
