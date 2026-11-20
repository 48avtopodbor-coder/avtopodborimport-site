import Link from "next/link";

export default function HeaderHomeLink() {
  return (
    <Link
      href="/"
      className="inline-flex min-h-10 shrink-0 items-center gap-2 whitespace-nowrap text-sm font-body text-gray-300 hover:text-orange-400 transition-colors"
    >
      <span aria-hidden="true">←</span>
      На главную
    </Link>
  );
}
