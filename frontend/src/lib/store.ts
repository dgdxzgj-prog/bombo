import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User, UserRole } from "@/types";
import { api } from "./api";

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  // Actions
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string, email: string) => Promise<void>;
  logout: () => Promise<void>;
  checkAuth: () => void;
  hasPermission: (permission: string) => boolean;
}

const permissionMap: Record<string, UserRole[]> = {
  view_videos: ["free", "vip", "admin"],
  search_videos: ["free", "vip", "admin"],
  view_ai_analysis: ["vip", "admin"],
  manage_channels: ["admin"],
  manage_users: ["admin"],
};

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,

      login: async (username: string, password: string) => {
        set({ isLoading: true });
        try {
          const response = await api.login({ username, password });
          localStorage.setItem("bombo_token", response.token);
          localStorage.setItem("bombo_user", JSON.stringify(response.user));
          set({
            user: response.user,
            token: response.token,
            isAuthenticated: true,
            isLoading: false,
          });
        } catch (error) {
          set({ isLoading: false });
          throw error;
        }
      },

      register: async (username: string, password: string, email: string) => {
        set({ isLoading: true });
        try {
          const response = await api.register({ username, password, email });
          localStorage.setItem("bombo_token", response.token);
          localStorage.setItem("bombo_user", JSON.stringify(response.user));
          set({
            user: response.user,
            token: response.token,
            isAuthenticated: true,
            isLoading: false,
          });
        } catch (error) {
          set({ isLoading: false });
          throw error;
        }
      },

      logout: async () => {
        try {
          await api.logout();
        } catch {
          // Ignore logout errors
        } finally {
          localStorage.removeItem("bombo_token");
          localStorage.removeItem("bombo_user");
          set({
            user: null,
            token: null,
            isAuthenticated: false,
          });
        }
      },

      checkAuth: () => {
        const token = localStorage.getItem("bombo_token");
        const userStr = localStorage.getItem("bombo_user");
        if (token && userStr) {
          try {
            const user = JSON.parse(userStr) as User;
            set({ isAuthenticated: true, user, token });
          } catch {
            localStorage.removeItem("bombo_token");
            localStorage.removeItem("bombo_user");
          }
        }
      },

      hasPermission: (permission: string) => {
        const { user } = get();
        if (!user) return false;

        if (user.role === "admin") return true;

        const allowedRoles = permissionMap[permission] || [];
        return allowedRoles.includes(user.role);
      },
    }),
    {
      name: "bombo-auth",
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);

export default useAuthStore;
