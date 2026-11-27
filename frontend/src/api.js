export async function api(path, options = {}) {
  const form = options.body instanceof FormData;
  const response = await fetch("/api" + path, {
    credentials: "include",
    ...options,
    headers: {
      ...(options.body && !form ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
    body: options.body && !form ? JSON.stringify(options.body) : options.body,
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = data?.detail;
    throw new Error(
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((x) => x.msg).join("; ")
          : `Request failed (${response.status}). Please retry.`,
    );
  }
  return data;
}
