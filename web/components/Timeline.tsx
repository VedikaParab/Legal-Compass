import type { T } from "@/lib/i18n";

const START = Date.UTC(2022, 0, 1);
const SWITCH = Date.UTC(2024, 6, 1);
const END = Math.max(Date.UTC(2026, 11, 31), Date.now());
const pos = (ms: number) => Math.min(100, Math.max(0, ((ms - START) / (END - START)) * 100));

/** IPC → BNS timeline with the 1 July 2024 switch and, optionally, a marker for the user's incident date. */
export default function Timeline({ t, date, dark = false }: { t: T; date?: string | null; dark?: boolean }) {
  const d = date ? Date.parse(date.slice(0, 10)) : NaN;
  const has = !Number.isNaN(d);
  const before = has && d < SWITCH;
  const sw = pos(SWITCH);
  const muted = dark ? "text-white/70" : "text-slate";
  return (
    <div aria-hidden={!has} className="select-none">
      <div className={`flex justify-between text-[11px] font-semibold uppercase tracking-wider ${muted}`}>
        <span>{t.tl_before}</span><span>{t.tl_after}</span>
      </div>
      <div className="relative mt-2 h-[4.25rem]">
        <div className="absolute inset-x-0 top-5 flex h-3 overflow-hidden rounded-full">
          <div style={{ width: `${sw}%` }} className={dark ? "bg-white/25" : "bg-ink/15"} />
          <div className="flex-1 bg-amber" />
        </div>
        {/* the switch */}
        <div style={{ left: `${sw}%` }} className="absolute top-2 -translate-x-1/2 text-center">
          <div className={`mx-auto h-9 w-0.5 ${dark ? "bg-white" : "bg-ink"}`} />
          <div className={`mt-0.5 whitespace-nowrap text-xs font-bold ${dark ? "text-white" : "text-ink"}`}>1 Jul 2024</div>
        </div>
        {has && (
          <div style={{ left: `${pos(d)}%` }} className="absolute -top-1 -translate-x-1/2 transition-all duration-500">
            <div className={`whitespace-nowrap rounded-md px-2 py-0.5 text-[11px] font-bold shadow ${before ? "bg-sky text-white" : "bg-ink text-amber"}`}>
              {t.tl_you}
            </div>
            <div className={`mx-auto mt-0.5 h-4 w-4 rounded-full border-2 border-white shadow ${before ? "bg-sky" : "bg-ink"}`} />
          </div>
        )}
      </div>
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div className={`rounded-lg px-3 py-2 ${before ? "bg-sky/15 ring-2 ring-sky" : dark ? "bg-white/10" : "bg-mist"}`}>
          <p className={`font-bold ${dark ? "text-white" : "text-ink"}`}>IPC</p>
          <p className={`text-xs ${muted}`}>{t.tl_ipc}</p>
        </div>
        <div className={`rounded-lg px-3 py-2 ${has && !before ? "bg-amber/25 ring-2 ring-amber" : dark ? "bg-white/10" : "bg-amber-soft"}`}>
          <p className={`font-bold ${dark ? "text-white" : "text-ink"}`}>BNS</p>
          <p className={`text-xs ${muted}`}>{t.tl_bns}</p>
        </div>
      </div>
    </div>
  );
}
