const STEPS = [
  {
    num: "01",
    title: "Выбираете авто",
    desc: "В каталоге находите машину по параметрам. Видите цену под ключ — с доставкой и растаможкой.",
  },
  {
    num: "02",
    title: "Оставляете заявку",
    desc: "Менеджер свяжется в течение 1 часа, уточнит детали и зафиксирует стоимость в договоре.",
  },
  {
    num: "03",
    title: "Подписываете договор",
    desc: "Работаем официально. Договор с фиксированной ценой и сроком — ваша гарантия.",
  },
  {
    num: "04",
    title: "Получаете автомобиль",
    desc: "Доставляем во Владивосток, Москву или Липецк. Всё оформление включено.",
  },
];

export default function HowToBuy() {
  return (
    <section className="bg-graphite-800/30 py-16 divider-orange">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <p className="text-orange-500 font-heading text-xs uppercase tracking-widest mb-3">
            Простой процесс
          </p>
          <h2 className="font-heading font-bold text-2xl sm:text-3xl text-white">
            Как купить авто из Китая
          </h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {STEPS.map((step) => (
            <div key={step.num} className="relative">
              <div className="font-heading font-bold text-5xl text-white/5 mb-3 leading-none">
                {step.num}
              </div>
              <div className="font-heading font-bold text-base text-white mb-2">
                {step.title}
              </div>
              <div className="font-body text-sm text-gray-400 leading-relaxed">
                {step.desc}
              </div>
            </div>
          ))}
        </div>

        {/* CTA */}
        <div className="mt-12 text-center">
          <a
            href="#contact"
            className="inline-flex items-center gap-3 bg-orange-500 hover:bg-orange-600 text-white font-body font-bold text-base px-8 py-4 rounded-xl transition-colors"
          >
            Получить консультацию бесплатно
          </a>
          <p className="text-gray-500 font-body text-xs mt-3">
            Офисы во Владивостоке, Москве и Липецке
          </p>
        </div>
      </div>
    </section>
  );
}
