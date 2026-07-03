"use client";
import { Users } from "lucide-react";
import UserManagement from "@/components/UserManagement";

export default function UsersPage() {
  return (
    <div className="h-full flex flex-col">
      <div className="h-14 border-b border-[#1e1e2e] px-5 flex items-center gap-2 shrink-0">
        <Users size={15} className="text-[#6366f1]" />
        <span className="font-semibold text-white">Team Management</span>
      </div>
      <div className="flex-1 overflow-auto p-6">
        <UserManagement />
      </div>
    </div>
  );
}
