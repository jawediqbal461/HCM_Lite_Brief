/** Frames a real app screenshot like a little browser window, so it reads as
 * product UI rather than a bare image dropped on the page. */
export default function BrowserFrame({ src, alt, caption }: { src: string; alt: string; caption?: string }) {
  return (
    <figure className="rounded-xl border border-slate-200 shadow-lg overflow-hidden bg-white">
      <div className="flex items-center gap-1.5 bg-slate-100 px-3 py-2 border-b border-slate-200">
        <span className="w-2.5 h-2.5 rounded-full bg-red-300" />
        <span className="w-2.5 h-2.5 rounded-full bg-amber-300" />
        <span className="w-2.5 h-2.5 rounded-full bg-green-300" />
      </div>
      <img src={src} alt={alt} loading="lazy" className="w-full h-auto block" />
      {caption && <figcaption className="px-3 py-2 text-xs text-slate-500 border-t border-slate-100">{caption}</figcaption>}
    </figure>
  );
}
