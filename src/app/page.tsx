import Header from "@/components/layout/Header";
import HeroSearch from "@/components/home/HeroSearch";
import CatalogEntry from "@/components/home/CatalogEntry";
import HowPriceWorks from "@/components/home/HowPriceWorks";
import LatestArrivals from "@/components/home/LatestArrivals";
import HowToBuy from "@/components/home/HowToBuy";
import Footer from "@/components/layout/Footer";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-graphite-900">
      <Header />
      <HeroSearch />
      <CatalogEntry />
      <HowPriceWorks />
      <LatestArrivals />
      <HowToBuy />
      <Footer />
    </main>
  );
}
