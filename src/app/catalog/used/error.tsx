"use client";
export default function Error({ reset }: { reset: () => void }) {
  return (
    <main className="mx-auto max-w-7xl px-4 py-10 text-white">
      <h1 className="font-heading text-2xl font-bold">Не удалось загрузить каталог</h1>
      <p className="mt-3 text-gray-400">Попробуйте ещё раз через несколько секунд.</p>
      <button
        type="button"
        onClick={reset}
        className="mt-5 min-h-11 rounded-lg bg-orange-500 px-5 font-semibold text-black"
      >
        Повторить
      </button>
    </main>
  );
}
