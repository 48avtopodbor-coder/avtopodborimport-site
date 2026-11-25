import { equipmentStatusLabels, type EquipmentGroup } from "@/lib/equipment";

export default function CarEquipment({ groups }: { groups: EquipmentGroup[] }) {
  if (!groups.length) return null;
  const count = groups.reduce((sum, group) => sum + group.items.length, 0);
  return (
    <section className="mt-10" aria-labelledby="car-equipment-title">
      <h2 id="car-equipment-title" className="font-heading font-bold text-lg text-white mb-2">
        Комплектация
      </h2>
      <p className="text-gray-400 font-body text-sm mb-4">
        Параметров по данным модели: {count}. Фактическое оснащение автомобиля уточняйте при
        осмотре. Дополнительное оборудование могло не устанавливаться.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-start">
        {groups.map(({ title, sourceTitle, items }, index) => (
          <details
            key={`${sourceTitle}:${index}`}
            open
            className="group bg-graphite-800 rounded-xl min-w-0"
          >
            <summary className="cursor-pointer rounded-xl px-5 py-4 font-heading font-bold text-white text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-orange-500 [overflow-wrap:anywhere]">
              {title}
              <span className="ml-2 font-body font-normal text-gray-400">{items.length}</span>
            </summary>
            <dl className="px-5 pb-5 divide-y divide-white/10">
              {items.map(({ label, sourceLabel, sourceValue, values, translationPending }) => (
                <div
                  key={JSON.stringify([sourceLabel, sourceValue])}
                  className="py-3 first:pt-0 [overflow-wrap:anywhere]"
                >
                  <dt className="text-white font-body text-sm">{label}</dt>
                  <dd className="mt-1 space-y-2 text-sm font-body">
                    {values.map(({ text, status, translationPending: pending }, valueIndex) => (
                      <div key={valueIndex}>
                        {text && <p className="text-gray-300">{text}</p>}
                        <p className="text-gray-400">{equipmentStatusLabels[status]}</p>
                        {pending && <p className="text-gray-400">Перевод значения уточняется.</p>}
                      </div>
                    ))}
                    {translationPending && (
                      <p className="text-gray-400">
                        Оригинал: {sourceLabel} — {sourceValue}
                      </p>
                    )}
                  </dd>
                </div>
              ))}
            </dl>
          </details>
        ))}
      </div>
      <details className="mt-4 rounded-xl border border-white/10 p-4 min-w-0 text-sm font-body">
        <summary className="cursor-pointer text-gray-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-orange-500">
          Показать оригинальные данные комплектации
        </summary>
        <div className="mt-4 space-y-5 [overflow-wrap:anywhere]">
          {groups.map(({ sourceTitle, items }, index) => (
            <div key={`${sourceTitle}:${index}`}>
              <h3 className="text-white mb-2">{sourceTitle}</h3>
              <dl className="space-y-3 text-gray-400">
                {items.map(({ sourceLabel, sourceValue }) => (
                  <div key={JSON.stringify([sourceLabel, sourceValue])}>
                    <dt>{sourceLabel}</dt>
                    <dd className="whitespace-pre-line">{sourceValue}</dd>
                  </div>
                ))}
              </dl>
            </div>
          ))}
        </div>
      </details>
    </section>
  );
}
