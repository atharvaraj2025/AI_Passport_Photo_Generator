import toast from "react-hot-toast";
import { cleanup } from "../services/api";
export function Settings() {
  return (
    <section
      id="settings"
      className="rounded-3xl bg-white/60 p-6 dark:bg-slate-900/60"
    >
      <h2 className="text-2xl font-bold dark:text-white">Settings</h2>
      <p className="mt-2 text-slate-600 dark:text-slate-300">
        Backend limits are controlled by the backend `.env`: image size, ZIP
        size, output dimensions, JPEG quality, and InsightFace provider.
      </p>
      <button
        onClick={() =>
          cleanup().then(() =>
            toast.success("Local uploads, outputs, and temp files deleted"),
          )
        }
        className="mt-5 rounded-2xl bg-red-600 px-5 py-3 font-semibold text-white"
      >
        Cleanup local files
      </button>
    </section>
  );
}
