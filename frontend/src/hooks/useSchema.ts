"use client";

import { useEffect, useState } from "react";
import { fetchSchema } from "@/lib/api";
import type { SchemaResponse } from "@/lib/types";

export function useSchema() {
  const [schema, setSchema] = useState<SchemaResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSchema()
      .then(setSchema)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return { schema, loading, error };
}
