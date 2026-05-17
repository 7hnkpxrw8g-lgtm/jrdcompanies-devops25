import { AuthGuard } from "@/components/app/auth-guard";
import { CommandPalette } from "@/components/app/command-palette";
import { Sidebar } from "@/components/app/sidebar";
import { Topbar } from "@/components/app/topbar";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <div className="flex min-h-screen">
        <Sidebar />
        <div className="flex flex-1 flex-col">
          <Topbar />
          <main className="flex-1 bg-background">
            <div className="container max-w-screen-2xl py-6">{children}</div>
          </main>
        </div>
        <CommandPalette />
      </div>
    </AuthGuard>
  );
}
