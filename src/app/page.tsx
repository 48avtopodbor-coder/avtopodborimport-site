import Header from "@/components/layout/Header";
import HeroSearch from "@/components/home/HeroSearch";
import CatalogEntry from "@/components/home/CatalogEntry";
import HowPriceWorks from "@/components/home/HowPriceWorks";
import LatestArrivals from "@/components/home/LatestArrivals";
import HowToBuy from "@/components/home/HowToBuy";
import Footer from "@/components/layout/Footer";
import { getCatalogSummary } from "@/lib/catalog-data";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const { total, priceAvailable } = await getCatalogSummary().catch((error: unknown) => {
    console.error("Не удалось загрузить сводку каталога", error);
    return { total: null, priceAvailable: false };
  });

  return (
    <main className="min-h-screen bg-graphite-900">
      <Header />
      <HeroSearch total={total} priceAvailable={priceAvailable} />
      <CatalogEntry total={total} />
      <HowPriceWorks />
      <LatestArrivals total={total} />
      <HowToBuy />
      <Footer />
    </main>
  );
}
