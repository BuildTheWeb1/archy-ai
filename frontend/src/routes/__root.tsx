import { createRootRoute, Outlet, Link } from "@tanstack/react-router";

export const Route = createRootRoute({
  component: RootLayout,
});

function RootLayout() {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Nav */}
      <nav className="bg-white border-b border-slate-200 px-6 py-3 flex items-center gap-3 shrink-0">
        <Link to="/" className="flex items-center gap-2 text-blue-700 hover:text-blue-800">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <span className="font-bold text-slate-900">Archy AI</span>
        </Link>
        <span className="text-slate-300 text-xs">CAD Extract — localhost demo</span>
      </nav>

      <main className="flex-1 flex flex-col">
        <Outlet />
      </main>
    </div>
  );
}
