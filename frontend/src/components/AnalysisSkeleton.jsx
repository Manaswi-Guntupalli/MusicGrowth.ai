export default function AnalysisSkeleton() {
  return (
    <div className="space-y-6">
      <div className="skeleton-blob min-h-[120px] p-6">
        <div className="skeleton-line mb-4 h-8 w-2/5" />
        <div className="skeleton-line mb-2 h-2 w-full" />
        <div className="skeleton-line h-4 w-1/3" />
      </div>

      <div className="flex gap-3 overflow-x-auto no-scrollbar pb-1">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div key={i} className="skeleton-line h-10 w-36 shrink-0" />
        ))}
      </div>

      <div className="skeleton-blob p-6">
        <div className="skeleton-line mb-3 h-6 w-48" />
        <div className="skeleton-line mb-6 h-4 w-72" />
        <div className="skeleton-blob h-[340px]" />
        <div className="mt-6 grid gap-3 md:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="skeleton-blob h-[92px]" />
          ))}
        </div>
      </div>

      <div className="grid gap-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="skeleton-blob h-24" />
        ))}
      </div>
    </div>
  )
}
