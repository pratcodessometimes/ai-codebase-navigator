import React from "react";
import { Sidebar } from "@/components/layout/Sidebar";

export const AppLayout = ({ children }) => (
  <div className="flex bg-white min-h-screen">
    <Sidebar />

    <main className="flex-1 min-w-0 px-8 py-10 lg:px-12">
      <div className="max-w-7xl mx-auto">
        {children}
      </div>
    </main>
  </div>
);