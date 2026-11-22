import Link from "next/link";
import BrandLogo from "./BrandLogo";
import {
  formatCarFullName,
  getBrandHref,
  getModelHref,
  legacyCarName,
  type CarTitleData,
} from "@/lib/car-title";

export default function CarTitle({ car }: { car: CarTitleData }) {
  if (!car.brand_id || !car.brand_name || !car.brand_slug || !car.model_name || !car.model_slug) {
    return (
      <h1 className="mb-1 font-heading text-2xl font-bold text-white [overflow-wrap:anywhere]">
        {legacyCarName(car)}
      </h1>
    );
  }

  const brandHref = getBrandHref(car.brand_slug);
  const modelHref = getModelHref(car.brand_slug, car.model_slug);
  return (
    <header className="mb-1 flex min-w-0 items-start gap-3 sm:gap-4">
      <Link href={brandHref} tabIndex={-1} aria-hidden="true" className="shrink-0">
        <BrandLogo name={car.brand_name} path={car.logo_path} />
      </Link>
      <h1
        className="min-w-0 font-heading text-white [overflow-wrap:anywhere]"
        title={formatCarFullName(car)}
      >
        <Link
          href={brandHref}
          title={`Все ${car.brand_name} в каталоге`}
          className="relative z-10 flex min-h-11 w-fit max-w-full items-center gap-1 text-xs font-medium uppercase tracking-[.14em] text-orange-400 hover:underline hover:decoration-2 hover:underline-offset-4 focus-visible:rounded-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[3px] focus-visible:outline-orange-400 sm:min-h-0 sm:py-2"
        >
          {car.brand_name}
          <svg aria-hidden="true" width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path
              d="m5 3 4 4-4 4"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </Link>{" "}
        <Link
          href={modelHref}
          title={`Все ${car.brand_name} ${car.model_name} в каталоге`}
          className="inline-block text-[26px] font-semibold leading-[1.1] hover:underline hover:decoration-orange-400 hover:decoration-2 hover:underline-offset-4 focus-visible:rounded-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[3px] focus-visible:outline-orange-400 sm:text-[34px]"
        >
          {car.model_name}
        </Link>{" "}
        <span className="sr-only">{car.year}</span>
        {car.trim && (
          <>
            {" "}
            <span className="ml-2 font-body text-[15px] font-light leading-snug text-gray-400 sm:ml-3 sm:text-lg">
              {car.trim}
            </span>
          </>
        )}
      </h1>
    </header>
  );
}
