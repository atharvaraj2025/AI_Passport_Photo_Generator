import { Camera, Moon, Sun } from "lucide-react";
import { useTheme } from "../contexts/ThemeContext";
export function Navbar() {
  const { dark, toggle } = useTheme();
  return (
    <header className="sticky top-0 z-20 border-b border-white/20 bg-white/60 backdrop-blur-xl dark:bg-slate-950/60">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4">
        <div className="flex items-center gap-3 font-bold text-slate-900 dark:text-white">
          <span className="rounded-2xl bg-gradient-to-br from-indigo-500 to-cyan-400 p-2 text-white">
            <Camera />
          </span>
          AI Passport Photo Generator
        </div>
        <nav className="hidden gap-6 text-sm font-medium text-slate-600 dark:text-slate-300 md:flex">
          <a href="#home">Home</a>
          <a href="#about">About</a>
          <a href="#settings">Settings</a>
          <a href="#history">History</a>
        </nav>
        <button
          onClick={toggle}
          className="rounded-full bg-white/70 p-2 shadow-glass dark:bg-slate-800"
        >
          {dark ? <Sun /> : <Moon />}
        </button>
      </div>
    </header>
  );
}
