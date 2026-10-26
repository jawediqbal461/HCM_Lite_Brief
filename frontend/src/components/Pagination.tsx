export default function Pagination({
  page,
  pageSize,
  total,
  onPage,
}: {
  page: number;
  pageSize: number;
  total: number;
  onPage: (next: number) => void;
}) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);

  return (
    <div className="flex items-center justify-between gap-3 px-2 py-2 text-sm text-slate-600 border-t">
      <span>
        {total === 0 ? "No results" : `${from}–${to} of ${total}`}
      </span>
      <div className="flex items-center gap-2">
        <button
          className="border rounded px-3 py-1 disabled:opacity-40 hover:bg-slate-50"
          onClick={() => onPage(page - 1)}
          disabled={page <= 1}
        >
          Previous
        </button>
        <span className="text-slate-500">
          Page {page} of {pages}
        </span>
        <button
          className="border rounded px-3 py-1 disabled:opacity-40 hover:bg-slate-50"
          onClick={() => onPage(page + 1)}
          disabled={page >= pages}
        >
          Next
        </button>
      </div>
    </div>
  );
}
