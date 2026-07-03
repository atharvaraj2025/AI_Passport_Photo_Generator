import { Toaster } from "react-hot-toast";
import { About } from "./pages/About";
import { Home } from "./pages/Home";
import { Settings } from "./pages/Settings";
import { AppLayout } from "./layouts/AppLayout";
export default function App() {
  return (
    <AppLayout>
      <Home />
      <div className="mt-8 grid gap-8 lg:grid-cols-2">
        <About />
        <Settings />
      </div>
      <Toaster position="top-right" />
    </AppLayout>
  );
}
