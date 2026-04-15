"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { Toaster } from "sonner";

import { QueryClientProvider } from "@/components/query-client-provider";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { WorkspaceSidebar } from "@/components/workspace/workspace-sidebar";

const CommandPalette = dynamic(() => import("@/components/workspace/command-palette").then((module) => module.CommandPalette), {
  ssr: false,
  loading: () => null,
});

export default function WorkspaceLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const [initialSidebarOpen, setInitialSidebarOpen] = useState<boolean | undefined>(undefined);

  useEffect(() => {
    const sidebarState = document.cookie
      .split("; ")
      .find((row) => row.startsWith("sidebar_state="))
      ?.split("=")[1];
    
    if (sidebarState === "true") setInitialSidebarOpen(true);
    if (sidebarState === "false") setInitialSidebarOpen(false);
  }, []);

  return (
    <QueryClientProvider>
      <SidebarProvider className="h-screen" defaultOpen={initialSidebarOpen}>
        <WorkspaceSidebar />
        <SidebarInset className="min-w-0">{children}</SidebarInset>
      </SidebarProvider>
      <CommandPalette />
      <Toaster position="top-center" />
    </QueryClientProvider>
  );
}
