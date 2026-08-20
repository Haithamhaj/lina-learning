import { SignUp } from "@clerk/nextjs";

export default function SignUpPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[#f5f7fb] px-5 py-10">
      <SignUp path="/sign-up" routing="path" signInUrl="/sign-in" />
    </main>
  );
}