"use client";

import { useAppStore } from "@/lib/store";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function SettingsPage() {
  const { user, entities } = useAppStore();
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground">Organization, entities, and platform config.</p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Your account</CardTitle>
          <CardDescription>Authenticated session details.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <div className="grid grid-cols-2 gap-2">
            <div className="text-muted-foreground">Email</div>
            <div className="font-medium">{user?.email}</div>
            <div className="text-muted-foreground">Name</div>
            <div className="font-medium">{user?.full_name}</div>
            <div className="text-muted-foreground">Organization</div>
            <div className="font-medium">{user?.org_slug}</div>
            <div className="text-muted-foreground">Role</div>
            <div>
              <Badge variant="outline" className="capitalize">{user?.role}</Badge>
            </div>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Entities</CardTitle>
          <CardDescription>Legal entities under your organization.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {entities.map((e) => (
            <div key={e.id} className="flex items-center justify-between border-b pb-2 last:border-0">
              <div>
                <div className="font-medium">{e.name}</div>
                <div className="text-xs text-muted-foreground">{e.legal_name ?? "—"}</div>
              </div>
              <Badge variant="outline" className="font-mono">{e.code}</Badge>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
