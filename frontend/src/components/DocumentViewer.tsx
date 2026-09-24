"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ChevronLeft,
  ChevronRight,
  Highlighter,
  Loader2,
  MessageSquareText,
  MousePointer2,
  RefreshCcw,
  Trash2,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import {
  createAnnotation,
  deleteAnnotation,
  getDocumentDetail,
  getDocumentVersionSignedUrl,
  listAnnotations,
  type AnnotationRectangle,
} from "@/lib/ragtutor";

type DragState = {
  startX: number;
  startY: number;
  currentX: number;
  currentY: number;
};

export function DocumentViewer({
  projectId,
  documentId,
}: {
  projectId: string;
  documentId: string;
}) {
  const queryClient = useQueryClient();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const overlayRef = useRef<HTMLDivElement | null>(null);
  const pdfRef = useRef<any>(null);

  const [versionId, setVersionId] = useState<string>("");
  const [signedUrl, setSignedUrl] = useState<string>("");
  const [pageNumber, setPageNumber] = useState(1);
  const [pageCount, setPageCount] = useState(0);
  const [zoom, setZoom] = useState(1);
  const [rendering, setRendering] = useState(false);
  const [drag, setDrag] = useState<DragState | null>(null);
  const [pendingRect, setPendingRect] = useState<AnnotationRectangle | null>(null);
  const [annotationType, setAnnotationType] = useState<"rectangle" | "text_highlight">("rectangle");
  const [selectedText, setSelectedText] = useState("");
  const [note, setNote] = useState("");
  const [color, setColor] = useState("#F4D06F");

  const document = useQuery({
    queryKey: ["document-detail", projectId, documentId],
    queryFn: () => getDocumentDetail(projectId, documentId),
  });

  const activeVersion = useMemo(() => {
    if (!document.data) return null;
    return (
      document.data.versions.find(
        (version) => version.id === document.data.active_version_id,
      ) ??
      document.data.versions[0] ??
      null
    );
  }, [document.data]);

  useEffect(() => {
    if (!versionId && activeVersion) {
      setVersionId(activeVersion.id);
    }
  }, [activeVersion, versionId]);

  const selectedVersion = useMemo(
    () => document.data?.versions.find((version) => version.id === versionId) ?? null,
    [document.data, versionId],
  );

  const annotations = useQuery({
    queryKey: ["annotations", projectId, documentId, versionId, pageNumber],
    queryFn: () =>
      listAnnotations(projectId, documentId, versionId, pageNumber),
    enabled: Boolean(versionId && selectedVersion?.mime_type === "application/pdf"),
  });

  const create = useMutation({
    mutationFn: async () => {
      if (!pendingRect || !versionId) throw new Error("No rectangle selected");
      return createAnnotation(projectId, documentId, versionId, {
        page_number: pageNumber,
        annotation_type: annotationType,
        selected_text: selectedText.trim() || null,
        rectangles: [pendingRect],
        content: note.trim() || null,
        color,
      });
    },
    onSuccess: async () => {
      setPendingRect(null);
      setSelectedText("");
      setNote("");
      await queryClient.invalidateQueries({
        queryKey: ["annotations", projectId, documentId, versionId, pageNumber],
      });
    },
  });

  const remove = useMutation({
    mutationFn: deleteAnnotation,
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["annotations", projectId, documentId, versionId, pageNumber],
      });
    },
  });

  useEffect(() => {
    if (!versionId || selectedVersion?.mime_type !== "application/pdf") return;

    let cancelled = false;

    async function loadPdf() {
      setRendering(true);
      try {
        const url = await getDocumentVersionSignedUrl(versionId);
        if (cancelled) return;
        setSignedUrl(url);

        const pdfjs = await import("pdfjs-dist");
        pdfjs.GlobalWorkerOptions.workerSrc = new URL(
          "pdfjs-dist/build/pdf.worker.min.mjs",
          import.meta.url,
        ).toString();

        const task = pdfjs.getDocument(url);
        const pdf = await task.promise;
        if (cancelled) return;

        pdfRef.current = pdf;
        setPageCount(pdf.numPages);
        setPageNumber((current) => Math.min(Math.max(1, current), pdf.numPages));
      } finally {
        if (!cancelled) setRendering(false);
      }
    }

    void loadPdf();

    return () => {
      cancelled = true;
      pdfRef.current?.destroy?.();
      pdfRef.current = null;
    };
  }, [versionId, selectedVersion?.mime_type]);

  useEffect(() => {
    const pdf = pdfRef.current;
    const canvas = canvasRef.current;
    if (!pdf || !canvas || pageNumber < 1) return;

    let cancelled = false;
    let renderTask: any;

    async function renderPage() {
      setRendering(true);
      try {
        const page = await pdf.getPage(pageNumber);
        if (cancelled) return;

        const baseViewport = page.getViewport({ scale: 1 });
        const containerWidth =
          overlayRef.current?.parentElement?.clientWidth ?? baseViewport.width;
        const fitScale = Math.max(
          0.6,
          Math.min(1.8, (containerWidth - 32) / baseViewport.width),
        );
        const viewport = page.getViewport({ scale: fitScale * zoom });

        const context = canvas.getContext("2d");
        if (!context) return;

        canvas.width = Math.floor(viewport.width);
        canvas.height = Math.floor(viewport.height);
        canvas.style.width = viewport.width + "px";
        canvas.style.height = viewport.height + "px";

        renderTask = page.render({
          canvasContext: context,
          viewport,
        });
        await renderTask.promise;
      } finally {
        if (!cancelled) setRendering(false);
      }
    }

    void renderPage();

    return () => {
      cancelled = true;
      renderTask?.cancel?.();
    };
  }, [pageNumber, zoom, signedUrl]);

  function pointerPosition(event: React.PointerEvent<HTMLDivElement>) {
    const target = overlayRef.current;
    if (!target) return null;
    const box = target.getBoundingClientRect();
    return {
      x: Math.max(0, Math.min(1, (event.clientX - box.left) / box.width)),
      y: Math.max(0, Math.min(1, (event.clientY - box.top) / box.height)),
    };
  }

  function onPointerDown(event: React.PointerEvent<HTMLDivElement>) {
    const point = pointerPosition(event);
    if (!point) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    setPendingRect(null);
    setDrag({
      startX: point.x,
      startY: point.y,
      currentX: point.x,
      currentY: point.y,
    });
  }

  function onPointerMove(event: React.PointerEvent<HTMLDivElement>) {
    if (!drag) return;
    const point = pointerPosition(event);
    if (!point) return;
    setDrag((current) =>
      current
        ? {
            ...current,
            currentX: point.x,
            currentY: point.y,
          }
        : null,
    );
  }

  function onPointerUp(event: React.PointerEvent<HTMLDivElement>) {
    if (!drag) return;
    const point = pointerPosition(event);
    const endX = point?.x ?? drag.currentX;
    const endY = point?.y ?? drag.currentY;
    const x = Math.min(drag.startX, endX);
    const y = Math.min(drag.startY, endY);
    const width = Math.abs(endX - drag.startX);
    const height = Math.abs(endY - drag.startY);

    setDrag(null);
    if (width < 0.005 || height < 0.005) return;
    setPendingRect({ x, y, width, height });
  }

  const liveRect = drag
    ? {
        x: Math.min(drag.startX, drag.currentX),
        y: Math.min(drag.startY, drag.currentY),
        width: Math.abs(drag.currentX - drag.startX),
        height: Math.abs(drag.currentY - drag.startY),
      }
    : null;

  if (document.isLoading) {
    return (
      <div className="grid min-h-[60vh] place-items-center">
        <Loader2 className="animate-spin text-[#b9634c]" />
      </div>
    );
  }

  if (document.isError || !document.data) {
    return (
      <div className="rounded-2xl bg-red-50 p-5 text-red-700">
        Không tải được document.
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1500px] space-y-5">
      <section className="flex flex-col justify-between gap-4 xl:flex-row xl:items-end">
        <div>
          <div className="font-hand text-2xl text-[#b9634c]">Read, highlight, remember</div>
          <h1 className="font-display text-4xl font-semibold">
            {document.data.display_name}
          </h1>
          <p className="mt-2 text-sm text-[#7d7167]">
            Annotation được gắn cố định với từng document version.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <select
            value={versionId}
            onChange={(event) => {
              setVersionId(event.target.value);
              setPageNumber(1);
              setPendingRect(null);
            }}
            className="rounded-2xl border border-[#705541]/15 bg-white/80 px-4 py-2.5 text-sm outline-none"
          >
            {document.data.versions.map((version) => (
              <option key={version.id} value={version.id}>
                v{version.version_number} · {version.status}
              </option>
            ))}
          </select>

          <button
            onClick={() => setZoom((value) => Math.max(0.6, value - 0.1))}
            className="grid h-10 w-10 place-items-center rounded-xl border border-[#705541]/12 bg-white/70"
          >
            <ZoomOut size={17} />
          </button>
          <div className="min-w-14 text-center text-sm text-[#75675c]">
            {Math.round(zoom * 100)}%
          </div>
          <button
            onClick={() => setZoom((value) => Math.min(2.2, value + 0.1))}
            className="grid h-10 w-10 place-items-center rounded-xl border border-[#705541]/12 bg-white/70"
          >
            <ZoomIn size={17} />
          </button>
        </div>
      </section>

      {selectedVersion?.mime_type !== "application/pdf" ? (
        <section className="paper-card rounded-[26px] p-8 text-center">
          <FileUnsupported />
          <h2 className="font-display mt-4 text-2xl font-semibold">
            Viewer annotation hiện hỗ trợ PDF
          </h2>
          <p className="mt-2 text-sm text-[#7d7167]">
            DOCX vẫn được ingest cho RAG nhưng chưa render annotation bằng PDF.js.
          </p>
        </section>
      ) : (
        <section className="grid gap-5 xl:grid-cols-[1fr_340px]">
          <div className="paper-card min-w-0 rounded-[26px] p-4">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <button
                  disabled={pageNumber <= 1}
                  onClick={() => setPageNumber((value) => Math.max(1, value - 1))}
                  className="grid h-9 w-9 place-items-center rounded-xl bg-white/70 disabled:opacity-40"
                >
                  <ChevronLeft size={17} />
                </button>
                <div className="rounded-xl bg-white/65 px-4 py-2 text-sm">
                  Page {pageNumber} / {pageCount || "…"}
                </div>
                <button
                  disabled={!pageCount || pageNumber >= pageCount}
                  onClick={() =>
                    setPageNumber((value) => Math.min(pageCount, value + 1))
                  }
                  className="grid h-9 w-9 place-items-center rounded-xl bg-white/70 disabled:opacity-40"
                >
                  <ChevronRight size={17} />
                </button>
              </div>

              {rendering && (
                <div className="flex items-center gap-2 text-xs text-[#8a7b70]">
                  <RefreshCcw size={14} className="animate-spin" />
                  Rendering...
                </div>
              )}
            </div>

            <div className="overflow-auto rounded-2xl bg-[#d8cec2] p-4">
              <div className="relative mx-auto w-fit shadow-xl">
                <canvas ref={canvasRef} className="block bg-white" />
                <div
                  ref={overlayRef}
                  onPointerDown={onPointerDown}
                  onPointerMove={onPointerMove}
                  onPointerUp={onPointerUp}
                  className="absolute inset-0 cursor-crosshair touch-none"
                >
                  {annotations.data?.flatMap((annotation) =>
                    (annotation.rectangles ?? []).map((rect, index) => (
                      <button
                        key={annotation.id + ":" + index}
                        type="button"
                        title={annotation.content || annotation.selected_text || "Annotation"}
                        className="absolute border-2 transition hover:brightness-95"
                        style={{
                          left: rect.x * 100 + "%",
                          top: rect.y * 100 + "%",
                          width: rect.width * 100 + "%",
                          height: rect.height * 100 + "%",
                          backgroundColor: annotation.color + "55",
                          borderColor: annotation.color,
                        }}
                      />
                    )),
                  )}

                  {(liveRect || pendingRect) && (
                    <div
                      className="pointer-events-none absolute border-2 border-dashed border-[#b9634c] bg-[#f4d06f]/25"
                      style={{
                        left: (liveRect ?? pendingRect)!.x * 100 + "%",
                        top: (liveRect ?? pendingRect)!.y * 100 + "%",
                        width: (liveRect ?? pendingRect)!.width * 100 + "%",
                        height: (liveRect ?? pendingRect)!.height * 100 + "%",
                      }}
                    />
                  )}
                </div>
              </div>
            </div>
          </div>

          <aside className="space-y-4">
            <div className="paper-card rounded-[24px] p-5">
              <div className="flex items-center gap-3">
                <div className="grid h-10 w-10 place-items-center rounded-xl bg-[#f3ddd4] text-[#9c513e]">
                  <MousePointer2 size={18} />
                </div>
                <div>
                  <h2 className="font-display text-xl font-semibold">Add annotation</h2>
                  <p className="text-xs text-[#8a7b70]">Kéo trực tiếp trên trang PDF.</p>
                </div>
              </div>

              <div className="mt-5 grid grid-cols-2 gap-2">
                <button
                  onClick={() => setAnnotationType("rectangle")}
                  className={
                    "rounded-xl px-3 py-2 text-xs font-semibold " +
                    (annotationType === "rectangle"
                      ? "bg-[#efd3c7] text-[#8f4738]"
                      : "bg-white/65 text-[#75675c]")
                  }
                >
                  Rectangle
                </button>
                <button
                  onClick={() => setAnnotationType("text_highlight")}
                  className={
                    "inline-flex items-center justify-center gap-1 rounded-xl px-3 py-2 text-xs font-semibold " +
                    (annotationType === "text_highlight"
                      ? "bg-[#f5e3c3] text-[#876225]"
                      : "bg-white/65 text-[#75675c]")
                  }
                >
                  <Highlighter size={14} />
                  Highlight
                </button>
              </div>

              {annotationType === "text_highlight" && (
                <textarea
                  rows={3}
                  value={selectedText}
                  onChange={(event) => setSelectedText(event.target.value)}
                  placeholder="Selected text / đoạn được highlight..."
                  className="mt-3 w-full resize-y rounded-xl border border-[#705541]/12 bg-white/70 p-3 text-sm outline-none"
                />
              )}

              <textarea
                rows={3}
                value={note}
                onChange={(event) => setNote(event.target.value)}
                placeholder="Ghi chú..."
                className="mt-3 w-full resize-y rounded-xl border border-[#705541]/12 bg-white/70 p-3 text-sm outline-none"
              />

              <div className="mt-3 flex items-center justify-between gap-3">
                <label className="flex items-center gap-2 text-xs text-[#75675c]">
                  Color
                  <input
                    type="color"
                    value={color}
                    onChange={(event) => setColor(event.target.value.toUpperCase())}
                    className="h-9 w-12 rounded border-0 bg-transparent"
                  />
                </label>

                <button
                  disabled={!pendingRect || create.isPending}
                  onClick={() => create.mutate()}
                  className="rounded-xl bg-[#b9634c] px-4 py-2 text-sm font-semibold text-white disabled:opacity-45"
                >
                  {create.isPending ? "Saving..." : "Save"}
                </button>
              </div>

              {pendingRect && (
                <button
                  onClick={() => setPendingRect(null)}
                  className="mt-3 text-xs font-medium text-[#8a7b70] underline"
                >
                  Bỏ vùng đang chọn
                </button>
              )}
            </div>

            <div className="paper-card rounded-[24px] p-5">
              <div className="flex items-center gap-2">
                <MessageSquareText size={18} className="text-[#9c513e]" />
                <h2 className="font-display text-xl font-semibold">
                  Page annotations
                </h2>
              </div>

              <div className="mt-4 space-y-2">
                {annotations.data?.map((annotation) => (
                  <div
                    key={annotation.id}
                    className="rounded-2xl border border-[#755640]/10 bg-white/58 p-3"
                  >
                    <div className="flex items-start gap-3">
                      <span
                        className="mt-1 h-4 w-4 shrink-0 rounded-full border border-black/10"
                        style={{ backgroundColor: annotation.color }}
                      />
                      <div className="min-w-0 flex-1">
                        <div className="text-xs font-semibold uppercase tracking-wide text-[#8a7b70]">
                          {annotation.annotation_type.replace("_", " ")}
                        </div>
                        {annotation.selected_text && (
                          <div className="mt-2 line-clamp-3 text-sm italic text-[#66584f]">
                            “{annotation.selected_text}”
                          </div>
                        )}
                        {annotation.content && (
                          <div className="mt-2 text-sm leading-6">
                            {annotation.content}
                          </div>
                        )}
                      </div>
                      <button
                        onClick={() => remove.mutate(annotation.id)}
                        className="grid h-8 w-8 shrink-0 place-items-center rounded-lg text-red-600 hover:bg-red-50"
                        title="Delete annotation"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                ))}

                {!annotations.isLoading && !annotations.data?.length && (
                  <div className="rounded-xl bg-white/45 p-4 text-sm text-[#8a7b70]">
                    Trang này chưa có annotation.
                  </div>
                )}
              </div>
            </div>
          </aside>
        </section>
      )}
    </div>
  );
}

function FileUnsupported() {
  return (
    <div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-[#f3ddd4] text-[#9c513e]">
      <MessageSquareText size={24} />
    </div>
  );
}
