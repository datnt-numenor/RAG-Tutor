import { PdfDocumentViewer } from "@/components/PdfDocumentViewer";

export default async function DocumentViewerPage({
  params,
  searchParams,
}: {
  params: Promise<{ projectId: string; documentId: string }>;
  searchParams: Promise<{ version?: string; page?: string }>;
}) {
  const [{ projectId, documentId }, query] = await Promise.all([
    params,
    searchParams,
  ]);

  const parsedPage = Number.parseInt(query.page ?? "1", 10);
  const initialPage =
    Number.isFinite(parsedPage) && parsedPage > 0 ? parsedPage : 1;

  return (
    <PdfDocumentViewer
      projectId={projectId}
      documentId={documentId}
      initialVersionId={query.version}
      initialPage={initialPage}
    />
  );
}
