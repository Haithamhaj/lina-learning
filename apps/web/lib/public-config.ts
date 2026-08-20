export const publicEnvironmentNames = [
  "development",
  "test",
  "production",
] as const;

export type PublicEnvironment = (typeof publicEnvironmentNames)[number];

export type PublicConfig = {
  appEnv: PublicEnvironment;
  apiBaseUrl: string;
};

function isPublicEnvironment(value: string): value is PublicEnvironment {
  return publicEnvironmentNames.includes(value as PublicEnvironment);
}

function loadPublicConfig(): PublicConfig {
  const appEnv = process.env.NEXT_PUBLIC_APP_ENV ?? "development";
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api";

  if (!isPublicEnvironment(appEnv)) {
    throw new Error(
      "NEXT_PUBLIC_APP_ENV must be development, test, or production.",
    );
  }

  if (!apiBaseUrl.trim()) {
    throw new Error("NEXT_PUBLIC_API_BASE_URL must not be empty.");
  }

  return Object.freeze({
    appEnv,
    apiBaseUrl,
  });
}

export const publicConfig = loadPublicConfig();