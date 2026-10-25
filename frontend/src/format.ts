const TZ = "Europe/London";
export const mw = (v: number | null | undefined, d = 0) =>
  v == null ? "n/a" : `${v.toLocaleString("en-GB", { maximumFractionDigits: d, minimumFractionDigits: d })} MW`;
export const pct = (v: number | null | undefined) => (v == null ? "n/a" : `${v.toFixed(1)}%`);
export const ukTime = (iso: string) =>
  new Date(iso).toLocaleString("en-GB", { timeZone: TZ, day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
export const ukClock = (iso: string) =>
  new Date(iso).toLocaleTimeString("en-GB", { timeZone: TZ, hour: "2-digit", minute: "2-digit" });
export const ukFull = (iso: string) =>
  new Date(iso).toLocaleString("en-GB", { timeZone: TZ, day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", timeZoneName: "short" });
