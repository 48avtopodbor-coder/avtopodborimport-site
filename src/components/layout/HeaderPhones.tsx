const phones = [
  { label: "8 (900) 600-65-15", href: "tel:+79006006515" },
  { label: "8 (904) 281-11-71", href: "tel:+79042811171" },
];

export const consultationHref = phones[0].href;

export default function HeaderPhones({ className = "" }: { className?: string }) {
  return (
    <div className={`flex gap-x-4 text-sm font-semibold tabular-nums text-white ${className}`}>
      {phones.map(({ label, href }) => (
        <a
          key={href}
          href={href}
          className="inline-flex min-h-8 sm:min-h-6 items-center whitespace-nowrap hover:text-orange-400 transition-colors"
        >
          {label}
        </a>
      ))}
    </div>
  );
}
