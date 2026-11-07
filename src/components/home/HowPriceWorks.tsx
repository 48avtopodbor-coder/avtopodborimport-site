export default function HowPriceWorks() {
  const steps = [
    {
      label: "Цена в Китае",
      example: "1 200 000 ₽",
      desc: "По текущему курсу юаня",
      icon: "🇨🇳",
    },
    {
      label: "Доставка",
      example: "+ 150 000 ₽",
      desc: "Владивосток → Липецк",
      icon: "🚢",
    },
    {
      label: "Таможня и утильсбор",
      example: "+ 480 000 ₽",
      desc: "По ставкам ЕАЭС",
      icon: "📋",
    },
    {
      label: "СБКТС и ЭПТС",
      example: "+ 60 000 ₽",
      desc: "Одобрение типа и электронный ПТС",
      icon: "📄",
    },
    {
      label: "Итого под ключ",
      example: "≈ 1 890 000 ₽",
      desc: "Предварительный расчёт",
      icon: "✅",
      accent: true,
    },
  ];

  return (
    <section className="bg-graphite-800/50 py-16 divider-orange">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-10">
          <p className="text-orange-500 font-heading text-xs uppercase tracking-widest mb-3">
            Прозрачное ценообразование
          </p>
          <h2 className="font-heading font-bold text-2xl sm:text-3xl text-white">
            Из чего складывается цена
          </h2>
        </div>

        <div className="flex flex-col sm:flex-row items-stretch gap-3 max-w-4xl mx-auto">
          {steps.map((step, i) => (
            <div key={step.label} className="flex sm:flex-col items-center gap-3 flex-1">
              {/* Карточка */}
              <div
                className={`w-full rounded-xl p-4 border transition-colors ${
                  step.accent
                    ? "bg-orange-500/10 border-orange-500/30"
                    : "bg-graphite-800 border-white/5"
                }`}
              >
                <div className="text-2xl mb-2">{step.icon}</div>
                <div className="font-heading font-bold text-sm text-white mb-1">
                  {step.label}
                </div>
                <div
                  className={`font-heading font-bold text-lg mb-1 ${
                    step.accent ? "text-orange-500" : "text-white"
                  }`}
                >
                  {step.example}
                </div>
                <div className="font-body text-xs text-gray-400">{step.desc}</div>
              </div>

              {/* Стрелка между шагами */}
              {i < steps.length - 1 && (
                <div className="text-gray-600 text-xl sm:rotate-90 flex-shrink-0">+</div>
              )}
            </div>
          ))}
        </div>

        <div className="text-center mt-8">
          <p className="text-gray-500 font-body text-xs mb-4">
            Расчёт предварительный. Точная цена и сроки — в договоре.
          </p>
          <a
            href="/price"
            className="inline-flex items-center gap-2 text-orange-500 hover:text-orange-400 font-body font-semibold text-sm transition-colors"
          >
            Рассчитать цену привоза
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M17 8l4 4m0 0l-4 4m4-4H3" />
            </svg>
          </a>
        </div>
      </div>
    </section>
  );
}
