"use client";

import { useUserId } from "@/lib/UserContext";

export default function UserIdInput() {
  const { userId, setUserId } = useUserId();
  return (
    <div className="flex items-center gap-2 text-sm">
      <label htmlFor="user-id" className="text-gray-600">
        User ID
      </label>
      <input
        id="user-id"
        type="text"
        value={userId}
        onChange={(e) => setUserId(e.target.value)}
        placeholder="paste a user_id"
        className="border border-gray-300 rounded px-2 py-1 w-80 font-mono text-xs"
      />
    </div>
  );
}