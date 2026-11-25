import { originalListingUrl } from "@/lib/original-listing";

export default function OriginalListingLink({
  url,
  listingId,
}: {
  url: string | null;
  listingId: string;
}) {
  const href = originalListingUrl(url, listingId);
  if (!href) return null;
  return (
    <div className="mt-4 border-t border-white/10 pt-3">
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex min-h-11 max-w-full items-center gap-2 rounded-md font-body text-sm text-orange-400 underline decoration-orange-400/40 underline-offset-4 transition-colors hover:text-orange-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-orange-400"
      >
        <svg
          aria-hidden="true"
          className="h-4 w-4 shrink-0"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.75"
        >
          <path d="M10 13a5 5 0 0 0 7 .1l3-3a5 5 0 0 0-7.1-7.1l-1.7 1.7M14 11a5 5 0 0 0-7-.1l-3 3a5 5 0 0 0 7.1 7.1l1.7-1.7" />
        </svg>
        <span className="min-w-0 [overflow-wrap:anywhere]">Оригинал объявления на Che168</span>
        <span className="sr-only"> (откроется в новой вкладке)</span>
      </a>
      <p className="font-body text-xs text-gray-400">Откроется в новой вкладке.</p>
    </div>
  );
}
