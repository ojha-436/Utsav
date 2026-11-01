// Thin fetch wrapper: JSON in/out, optional Firebase token, uniform errors.

let tokenProvider = null;

export function setTokenProvider(fn) {
  tokenProvider = fn;
}

export class ApiError extends Error {
  constructor(status, code, message) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

export async function api(path, { method = "GET", body, form } = {}) {
  const headers = {};
  if (tokenProvider) {
    const token = await tokenProvider();
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  let payload;
  if (form) {
    payload = form;
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  let res;
  try {
    res = await fetch(path, { method, headers, body: payload });
  } catch {
    throw new ApiError(0, "network", "Can't reach Utsav right now. Check your connection and try again.");
  }

  const type = res.headers.get("content-type") || "";
  if (!res.ok) {
    let code = "http_error";
    let message = `Something went wrong (${res.status}).`;
    if (type.includes("application/json")) {
      const data = await res.json().catch(() => ({}));
      code = data.error?.code ?? code;
      message = data.error?.message ?? message;
    }
    throw new ApiError(res.status, code, message);
  }
  if (res.status === 204) return null;
  return type.includes("application/json") ? res.json() : res.blob();
}
