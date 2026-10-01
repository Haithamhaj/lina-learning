const getToken = async () => "disposable-fixture-token";

// This fixture mounts the real Daily component without contacting Clerk.
export function useAuth() {
  return { getToken, isLoaded: true };
}
