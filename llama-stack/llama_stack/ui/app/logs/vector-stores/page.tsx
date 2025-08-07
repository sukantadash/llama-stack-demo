"use client";

import React from "react";
import { useAuthClient } from "@/hooks/use-auth-client";
import type {
  ListVectorStoresResponse,
  VectorStore,
} from "llama-stack-client/resources/vector-stores/vector-stores";
import { useRouter } from "next/navigation";
import { usePagination } from "@/hooks/use-pagination";
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";

export default function VectorStoresPage() {
  const client = useAuthClient();
  const router = useRouter();
  const {
    data: stores,
    status,
    hasMore,
    error,
    loadMore,
  } = usePagination<VectorStore>({
    limit: 20,
    order: "desc",
    fetchFunction: async (client, params) => {
      const response = await client.vectorStores.list({
        after: params.after,
        limit: params.limit,
        order: params.order,
      } as any);
      return response as ListVectorStoresResponse;
    },
    errorMessagePrefix: "vector stores",
  });

  // Auto-load all pages for infinite scroll behavior (like Responses)
  React.useEffect(() => {
    if (status === "idle" && hasMore) {
      loadMore();
    }
  }, [status, hasMore, loadMore]);

  if (status === "loading") {
    return (
      <div className="space-y-2">
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-full" />
      </div>
    );
  }

  if (status === "error") {
    return <div className="text-destructive">Error: {error?.message}</div>;
  }

  if (!stores || stores.length === 0) {
    return <p>No vector stores found.</p>;
  }

  return (
    <div className="overflow-auto flex-1 min-h-0">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>ID</TableHead>
            <TableHead>Name</TableHead>
            <TableHead>Created</TableHead>
            <TableHead>Completed</TableHead>
            <TableHead>Cancelled</TableHead>
            <TableHead>Failed</TableHead>
            <TableHead>In Progress</TableHead>
            <TableHead>Total</TableHead>
            <TableHead>Usage Bytes</TableHead>
            <TableHead>Provider ID</TableHead>
            <TableHead>Provider Vector DB ID</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {stores.map((store) => {
            const fileCounts = store.file_counts;
            const metadata = store.metadata || {};
            const providerId = metadata.provider_id ?? "";
            const providerDbId = metadata.provider_vector_db_id ?? "";

            return (
              <TableRow
                key={store.id}
                onClick={() => router.push(`/logs/vector-stores/${store.id}`)}
                className="cursor-pointer hover:bg-muted/50"
              >
                <TableCell>{store.id}</TableCell>
                <TableCell>{store.name}</TableCell>
                <TableCell>
                  {new Date(store.created_at * 1000).toLocaleString()}
                </TableCell>
                <TableCell>{fileCounts.completed}</TableCell>
                <TableCell>{fileCounts.cancelled}</TableCell>
                <TableCell>{fileCounts.failed}</TableCell>
                <TableCell>{fileCounts.in_progress}</TableCell>
                <TableCell>{fileCounts.total}</TableCell>
                <TableCell>{store.usage_bytes}</TableCell>
                <TableCell>{providerId}</TableCell>
                <TableCell>{providerDbId}</TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
