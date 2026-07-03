import { Navbar } from "../components/Navbar";
import { Sidebar } from "../components/Sidebar";
import { Footer } from "../components/Footer";
export function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-cyan-50 text-slate-900 dark:from-slate-950 dark:via-slate-900 dark:to-indigo-950">
      <Navbar />
      <main className="mx-auto flex max-w-7xl gap-8 px-4 py-8">
        <Sidebar />
        <div className="min-w-0 flex-1">
          {children}
          <Footer />
        </div>
      </main>
    </div>
  );
}
