/** A URL session ID locates server state; it never grants ownership or subject scope. */
export function dailySessionRequest(href: string): { learning_session_id?: string } {
  const reference = new URL(href).searchParams.get("session");
  return reference === null ? {} : { learning_session_id: reference };
}

export function dailySessionUrl(href: string, sessionId: string | null): string {
  const url = new URL(href);
  if (sessionId === null) url.searchParams.delete("session");
  else url.searchParams.set("session", sessionId);
  return `${url.pathname}${url.search}${url.hash}`;
}
