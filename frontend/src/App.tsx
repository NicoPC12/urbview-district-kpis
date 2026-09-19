import { useHealth } from '@/api/useHealth';
import { HealthLine } from '@/components/ui/HealthLine';

const APP_NAME = 'UrbView';

/** Phase 1 shell: the app name and the backend health probe. Map and dashboard land in Phase 5. */
export function App() {
  const health = useHealth();

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col gap-6 p-8 font-sans text-slate-900">
      <header>
        <h1 className="text-3xl font-semibold tracking-tight">{APP_NAME}</h1>
        <p className="text-slate-600">Urban safety KPIs from Overture Maps.</p>
      </header>

      <section aria-labelledby="health-heading" className="rounded-lg border border-slate-200 p-4">
        <h2 id="health-heading" className="text-sm font-medium uppercase text-slate-500">
          Backend
        </h2>
        <HealthLine state={health} />
      </section>
    </main>
  );
}
