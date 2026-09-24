import { PdfDocumentViewer } from "@/components/PdfDocumentViewer";

export default async function DocumentViewerPage({
  params,
}: {
  params: Promise<{ projectId: string; documentId: string }>;
}) {
  const { projectId, documentId } = await params;
  return (
    <PdfDocumentViewer projectId={projectId} documentId={documentId} />
  );
}
