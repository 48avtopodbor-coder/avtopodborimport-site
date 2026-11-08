export default function Loading() {
  return (
    <div className="min-h-screen bg-graphite-900 flex items-center justify-center">
      <div className="text-center">
        <div className="w-12 h-12 bg-orange-500 rounded-xl flex items-center justify-center mx-auto mb-4">
          <span className="font-bold text-white text-lg">AI</span>
        </div>
        <div className="text-gray-400 text-sm">Загрузка...</div>
      </div>
    </div>
  );
}
