import { SignUp } from "@clerk/nextjs";

export default function SignUpPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/30 px-4">
      <SignUp
        fallbackRedirectUrl="/create-business"
        signInUrl="/sign-in"
      />
    </div>
  );
}
