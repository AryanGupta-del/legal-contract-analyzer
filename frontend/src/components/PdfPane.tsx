import { FileText } from "lucide-react";
import { pdfUrl } from "../api";

export default function PdfPane({ id, name, page }: { id: string; name: string; page: number }) {
  return (
    <div className="flex h-full flex-col bg-slate-100">
      <div className="flex items-center gap-2 border-b border-slate-200 bg-white px-4 py-2 text-sm">
        <FileText className="h-4 w-4 text-brand-600" />
        <span className="truncate font-medium">{name}</span>
        <span className="ml-auto rounded-full bg-brand-50 px-2.5 py-0.5 text-xs font-medium text-brand-700">Page {page}</span>
      </div>
      {/* key forces a reload so the viewer jumps to the cited page */}
      <iframe key={`${id}-${page}`} title="Contract PDF" src={pdfUrl(id, page)} className="w-full flex-1 border-0" />
    </div>
  );
}
