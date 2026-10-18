import type { NavIconName } from "../auth/navigation";

export function BuildingMark({ className }: { className?: string }) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      viewBox="0 0 40 40"
      fill="none"
    >
      <rect width="40" height="40" rx="11" fill="currentColor" />
      <path
        d="M7 32V20h8v12M14 32V12h13v20M26 32V17h7v15"
        fill="white"
        opacity=".96"
      />
      <path
        d="M17 16h3v3h-3zm5 0h3v3h-3zm-5 6h3v3h-3zm5 0h3v3h-3zM9 23h3v3H9zm19-3h3v3h-3z"
        fill="currentColor"
      />
      <path d="M18 28h5v4h-5z" fill="currentColor" />
    </svg>
  );
}

export function SectionIcon({
  name,
  className,
}: {
  name: NavIconName;
  className?: string;
}) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {name === "overview" && (
        <>
          <rect x="3.5" y="3.5" width="7" height="7" rx="1.5" />
          <rect x="13.5" y="3.5" width="7" height="7" rx="1.5" />
          <rect x="3.5" y="13.5" width="7" height="7" rx="1.5" />
          <rect x="13.5" y="13.5" width="7" height="7" rx="1.5" />
        </>
      )}
      {name === "units" && (
        <>
          <path d="m3 10 9-7 9 7" />
          <path d="M5.5 9v11.5h13V9M9 20.5v-7h6v7" />
        </>
      )}
      {name === "properties" && (
        <>
          <path d="M3.5 20.5h17M5.5 20.5V6.5l7-3v17M12.5 20.5v-11l6-2.5v13.5" />
          <path d="M8.5 8.5h1m-1 4h1m6-1h1m-1 4h1" />
        </>
      )}
      {name === "users" && (
        <>
          <circle cx="9" cy="8" r="3.5" />
          <path d="M2.5 20v-1.5a6.5 6.5 0 0 1 13 0V20zM16 4.8a3.5 3.5 0 0 1 0 6.5m2 3a5.5 5.5 0 0 1 3.5 5.2V20h-3" />
        </>
      )}
      {name === "assignments" && (
        <>
          <circle cx="8" cy="8" r="3.5" />
          <path d="M2.5 20v-1.5a5.5 5.5 0 0 1 11 0V20zM15 11l2 2 4-4" />
        </>
      )}
      {name === "bills" && (
        <>
          <path d="M6 3.5h12v17l-3-1.8-3 1.8-3-1.8-3 1.8z" />
          <path d="M9 8h6m-6 4h6m-6 4h3" />
        </>
      )}
      {name === "incidences" && (
        <>
          <path d="m14.5 6.5 3-3a4 4 0 0 1-5 5l-7.8 7.8a2.1 2.1 0 0 0 3 3l7.8-7.8a4 4 0 0 0 5-5l-3 3z" />
        </>
      )}
      {name === "initiatives" && (
        <>
          <path d="M12 3.5a7 7 0 0 0-4.5 12.4c.8.7 1.2 1.5 1.2 2.6h6.6c0-1.1.4-1.9 1.2-2.6A7 7 0 0 0 12 3.5zM9 21h6m-5.5-2.5h5" />
          <path d="M12 1v1m9 10h-1M4 12H3m15.4-6.4-.7.7M6.3 6.3l-.7-.7" />
        </>
      )}
    </svg>
  );
}
