"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Entity, User } from "./types";

interface AppState {
  user: User | null;
  setUser: (u: User | null) => void;

  activeEntityId: string | null;
  entities: Entity[];
  setEntities: (entities: Entity[]) => void;
  setActiveEntityId: (id: string | null) => void;

  theme: "light" | "dark" | "system";
  setTheme: (t: "light" | "dark" | "system") => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      user: null,
      setUser: (user) => set({ user }),

      activeEntityId: null,
      entities: [],
      setEntities: (entities) =>
        set((state) => ({
          entities,
          activeEntityId:
            state.activeEntityId && entities.some((e) => e.id === state.activeEntityId)
              ? state.activeEntityId
              : entities[0]?.id ?? null,
        })),
      setActiveEntityId: (id) => set({ activeEntityId: id }),

      theme: "system",
      setTheme: (theme) => set({ theme }),
    }),
    {
      name: "jrd-app-state",
      partialize: (state) => ({
        activeEntityId: state.activeEntityId,
        theme: state.theme,
      }),
    }
  )
);
