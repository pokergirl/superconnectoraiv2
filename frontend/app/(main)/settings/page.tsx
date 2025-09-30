"use client";

import { useState, useEffect } from "react";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/context/AuthContext";
import { updateUserPreferences } from "@/lib/api";

export default function SettingsPage() {
  const { user, token } = useAuth();
  const [persistSearchResults, setPersistSearchResults] = useState(true);

  useEffect(() => {
    if (user) {
      setPersistSearchResults(user.persist_search_results);
    }
  }, [user]);

  const handleToggle = async (value: boolean) => {
    setPersistSearchResults(value);
    if (token) {
      try {
        await updateUserPreferences(token, {
          persist_search_results: value,
        });
      } catch (error) {
        console.error("Failed to update user preferences", error);
      }
    }
  };

  return (
    <div className="container mx-auto py-10">
      <h1 className="text-2xl font-bold mb-4">Settings</h1>
      <div className="flex items-center space-x-2">
        <Switch
          id="persist-search-results"
          checked={persistSearchResults}
          onCheckedChange={handleToggle}
        />
        <Label htmlFor="persist-search-results">
          Persist search results across sessions
        </Label>
      </div>
    </div>
  );
}