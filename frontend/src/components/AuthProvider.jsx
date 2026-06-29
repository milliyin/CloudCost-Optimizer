import { createContext, useContext, useEffect, useRef, useState } from "react";

import { registerAuthHooks } from "../api/client";

const AuthContext = createContext(null);

const emptySession = {
  user: null,
  accessToken: null,
  refreshToken: null,
};

export function AuthProvider({ children }) {
  const [session, setSession] = useState(emptySession);
  const sessionRef = useRef(session);

  useEffect(() => {
    sessionRef.current = session;
  }, [session]);

  useEffect(() => {
    registerAuthHooks({
      getAuthState: () => sessionRef.current,
      actions: {
        updateTokens(tokens) {
          setSession((currentSession) => ({
            ...currentSession,
            accessToken: tokens.access_token,
            refreshToken: tokens.refresh_token,
          }));
        },
        clearSession() {
          setSession(emptySession);
        },
      },
    });
  }, []);

  const value = {
    user: session.user,
    accessToken: session.accessToken,
    refreshToken: session.refreshToken,
    isAuthenticated: Boolean(session.accessToken && session.user),
    login(payload) {
      setSession({
        user: payload.user,
        accessToken: payload.tokens.access_token,
        refreshToken: payload.tokens.refresh_token,
      });
    },
    logout() {
      setSession(emptySession);
    },
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return value;
}
