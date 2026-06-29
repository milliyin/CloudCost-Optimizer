let authStateGetter = null;
let authActions = null;
let refreshPromise = null;

export function registerAuthHooks({ getAuthState, actions }) {
  authStateGetter = getAuthState;
  authActions = actions;
}

async function refreshTokens() {
  if (!authStateGetter || !authActions) {
    throw new Error("Auth hooks are not registered");
  }

  const { refreshToken } = authStateGetter();
  if (!refreshToken) {
    throw new Error("No refresh token available");
  }

  const response = await fetch("/auth/refresh", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!response.ok) {
    throw new Error("Session refresh failed");
  }

  const tokens = await response.json();
  authActions.updateTokens(tokens);
  return tokens;
}

export async function apiFetch(path, options = {}) {
  if (!authStateGetter || !authActions) {
    throw new Error("API client is not ready");
  }

  const state = authStateGetter();
  const headers = new Headers(options.headers ?? {});
  headers.set("Content-Type", headers.get("Content-Type") ?? "application/json");

  if (state.accessToken) {
    headers.set("Authorization", `Bearer ${state.accessToken}`);
  }

  const response = await fetch(path, {
    ...options,
    headers,
  });

  if (response.status !== 401 || path === "/auth/refresh") {
    return response;
  }

  if (!state.refreshToken) {
    authActions.clearSession();
    return response;
  }

  if (!refreshPromise) {
    refreshPromise = refreshTokens().finally(() => {
      refreshPromise = null;
    });
  }

  try {
    const newTokens = await refreshPromise;
    const retryHeaders = new Headers(options.headers ?? {});
    retryHeaders.set("Content-Type", retryHeaders.get("Content-Type") ?? "application/json");
    retryHeaders.set("Authorization", `Bearer ${newTokens.access_token}`);

    return await fetch(path, {
      ...options,
      headers: retryHeaders,
    });
  } catch (error) {
    authActions.clearSession();
    throw error;
  }
}
