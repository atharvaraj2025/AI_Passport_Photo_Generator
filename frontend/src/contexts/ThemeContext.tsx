import { createContext, useContext, useEffect, useMemo, useState } from 'react';
type ThemeContextValue = { dark: boolean; toggle: () => void };
const ThemeContext = createContext<ThemeContextValue | null>(null);
export function ThemeProvider({ children }: { children: React.ReactNode }) { const [dark, setDark] = useState(() => localStorage.theme === 'dark'); useEffect(() => { document.documentElement.classList.toggle('dark', dark); localStorage.theme = dark ? 'dark' : 'light'; }, [dark]); const value = useMemo(() => ({ dark, toggle: () => setDark(v => !v) }), [dark]); return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>; }
export function useTheme() { const ctx = useContext(ThemeContext); if (!ctx) throw new Error('useTheme must be used inside ThemeProvider'); return ctx; }
