export const USER_ROLES = {
  PARENT_ADMIN: "PARENT_ADMIN",
  STUDENT: "STUDENT",
} as const;

export type UserRole = (typeof USER_ROLES)[keyof typeof USER_ROLES];

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null
    ? (value as Record<string, unknown>)
    : null;
}

function readRole(value: unknown): UserRole | null {
  if (value === USER_ROLES.PARENT_ADMIN || value === USER_ROLES.STUDENT) {
    return value;
  }
  return null;
}

export function roleFromClaims(claims: unknown): UserRole {
  const record = asRecord(claims);
  if (!record) return USER_ROLES.STUDENT;

  const direct = readRole(record.role);
  if (direct) return direct;

  for (const key of [
    "metadata",
    "public_metadata",
    "publicMetadata",
    "unsafe_metadata",
  ]) {
    const nested = readRole(asRecord(record[key])?.role);
    if (nested) return nested;
  }

  return USER_ROLES.STUDENT;
}