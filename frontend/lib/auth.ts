import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";
import { useAuthStore } from "./auth-store";
import type { MeResponse, TokenPairResponse } from "./types";

export function useLogin() {
  const setSession = useAuthStore((s) => s.setSession);
  const setRolesAndPermissions = useAuthStore((s) => s.setRolesAndPermissions);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: { email: string; password: string }) =>
      api.post<TokenPairResponse>("/auth/login", data),
    onSuccess: async (data) => {
      setSession({
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        user: data.user,
      });
      const me = await api.get<MeResponse>("/auth/me");
      setRolesAndPermissions(me.roles, me.permissions);
      await queryClient.invalidateQueries();
    },
  });
}

export function useRegister() {
  return useMutation({
    mutationFn: (data: { email: string; password: string; full_name: string }) =>
      api.post("/auth/register", data),
  });
}

export function useMe(enabled: boolean) {
  return useQuery({
    queryKey: ["auth", "me"],
    queryFn: () => api.get<MeResponse>("/auth/me"),
    enabled,
    retry: false,
  });
}

export async function logout(): Promise<void> {
  const { refreshToken, clearSession } = useAuthStore.getState();
  if (refreshToken) {
    await api.post("/auth/logout", { refresh_token: refreshToken }).catch(() => undefined);
  }
  clearSession();
}
