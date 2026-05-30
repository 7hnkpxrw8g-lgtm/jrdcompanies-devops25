"use client";

import { CheckCircle2, AlertCircle, Info, X } from "lucide-react";
import { createContext, useCallback, useContext, useState } from "react";
import { cn } from "@/lib/utils";

type ToastVariant = "default" | "success" | "destructive" | "info";

interface Toast {
  id: number;
  title: string;
  description?: string;
  variant: ToastVariant;
}

interface ToastContextValue {
  toast: (t: Omit<Toast, "id" | "variant"> & { variant?: ToastVariant }) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const toast = useCallback<ToastContextValue["toast"]>((t) => {
    const id = Date.now() + Math.random();
    setToasts((p) => [...p, { id, variant: "default", ...t }]);
    window.setTimeout(() => {
      setToasts((p) => p.filter((x) => x.id !== id));
    }, 5000);
  }, []);

  function dismiss(id: number) {
    setToasts((p) => p.filter((x) => x.id !== id));
  }

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
        {toasts.map((t) => {
          const Icon =
            t.variant === "success"
              ? CheckCircle2
              : t.variant === "destructive"
              ? AlertCircle
              : Info;
          return (
            <div
              key={t.id}
              className={cn(
                "flex items-start gap-3 rounded-lg border bg-card p-3 shadow-lg animate-slide-up",
                t.variant === "success" && "border-success/40 bg-success/5",
                t.variant === "destructive" && "border-destructive/40 bg-destructive/5",
                t.variant === "info" && "border-primary/40 bg-primary/5"
              )}
            >
              <Icon
                className={cn(
                  "h-4 w-4 mt-0.5 shrink-0",
                  t.variant === "success" && "text-success",
                  t.variant === "destructive" && "text-destructive",
                  t.variant === "info" && "text-primary"
                )}
              />
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium">{t.title}</div>
                {t.description ? (
                  <div className="text-xs text-muted-foreground mt-0.5">
                    {t.description}
                  </div>
                ) : null}
              </div>
              <button
                onClick={() => dismiss(t.id)}
                className="text-muted-foreground hover:text-foreground"
                aria-label="Dismiss"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}
