import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';

import { Dashboard } from '@/features/dashboard/Dashboard';
import { MapView } from '@/features/map/MapView';

const APP_NAME = 'UrbView';

/** Map left (~60 %), dashboard right, one store between them. Desktop only (README). */
export function App() {
  const [client] = useState(() => new QueryClient());

  return (
    <QueryClientProvider client={client}>
      <div className="grid h-screen grid-cols-[3fr_2fr] font-sans text-slate-900">
        <main className="relative h-full min-h-0">
          <MapView />
        </main>
        <aside className="h-full min-h-0 overflow-y-auto border-l border-slate-200 p-4">
          <h1 className="text-xl font-semibold tracking-tight">{APP_NAME}</h1>
          <Dashboard />
        </aside>
      </div>
    </QueryClientProvider>
  );
}
