"use client";

import { PointerEvent, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ChevronLeft,
  ChevronRight,
  Highlighter,
  Loader2,
  MessageSquareText,
  Trash2,
} from "lucide-react";
import type { PDFDocumentProxy } from "pdfjs-dist";
import {
  createAnnotation,
  deleteAnnotation,
  getDocumentDetail,
  getDocumentVersionSignedUrl,
  listAnnotations,
  updateAnnotation,
  type AnnotationRectangle,
} from "@/lib/ragtutor";

type DraftRect = AnnotationRectangle | null;

export function PdfDocumentViewer({
  projectId,
  documentId,
  initialVersionId,
  initialPage = 1,
}: {
  projectId: string;
  documentId: string;
  initialVersionId?: string;
  initialPage?: number;
}) {
  const queryClient = useQueryClient();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const textLayerRef = useRef<HTMLDivElement | null>(null);
  const overlayRef = useRef<HTMLDivElement | null>(null);
  const dragStart = useRef<{ x: number; y: number } | null>(null);

  const [selectedVersionId, setSelectedVersionId] = useState<string>(
    initialVersionId ?? "",
  );
  const [pdf, setPdf] = useState<PDFDocumentProxy | null>(null);
  const [pageNumber, setPageNumber] = useState(
    Math.max(1, initialPage),
  );
  const [scale, setScale] = useState(1.25);
  const [draftRect, setDraftRect] = useState<DraftRect>(null);
  const [annotationMode, setAnnotationMode] = useState<"rectangle" | "text">(
    "rectangle",
  );
  const [color, setColor] = useState("#F4D06F");
  const [loadingPdf, setLoadingPdf] = useState(false);

  const detail = useQuery({
    queryKey: ["document-detail", projectId, documentId],
    queryFn: () => getDocumentDetail(projectId, documentId),
  });

  const activeVersionId = detail.data?.active_version_id ?? "";
  const effectiveVersionId =
    selectedVersionId || activeVersionId || detail.data?.versions?.[0]?.id || "";

  const selectedVersion = useMemo(
    () =>
      detail.data?.versions.find((version) => version.id === effectiveVersionId) ??
      null,
    [detail.data?.versions, effectiveVersionId],
  );

  const signedUrl = useQuery({
    queryKey: ["document-signed-url", effectiveVersionId],
    queryFn: () => getDocumentVersionSignedUrl(effectiveVersionId),
    enabled:
      Boolean(effectiveVersionId) &&
      selectedVersion?.mime_type === "application/pdf",
    staleTime: 4 * 60 * 1000,
  });

  const annotations = useQuery({
    queryKey: [
      "annotations",
      projectId,
      documentId,
      effectiveVersionId,
      pageNumber,
    ],
    queryFn: () =>
      listAnnotations(
        projectId,
        documentId,
        effectiveVersionId,
        pageNumber,
      ),
    enabled:
      Boolean(effectiveVersionId) &&
      selectedVersion?.mime_type === "application/pdf",
  });

  const create = useMutation({
    mutationFn: (payload: {
      rectangles: AnnotationRectangle[];
      note: string | null;
      annotationType: "rectangle" | "text_highlight";
      selectedText?: string | null;
    }) =>
      createAnnotation(projectId, documentId, effectiveVersionId, {
        page_number: pageNumber,
        annotation_type: payload.annotationType,
        rectangles: payload.rectangles,
        selected_text: payload.selectedText ?? null,
        content: payload.note,
        color,
      }),
    onSuccess: async () => {
      setDraftRect(null);
      await queryClient.invalidateQueries({
        queryKey: [
          "annotations",
          projectId,
          documentId,
          effectiveVersionId,
          pageNumber,
        ],
      });
    },
  });

  const remove = useMutation({
    mutationFn: deleteAnnotation,
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: [
          "annotations",
          projectId,
          documentId,
          effectiveVersionId,
          pageNumber,
        ],
      });
    },
  });

  const editNote = useMutation({
    mutationFn: ({
      annotationId,
      content,
    }: {
      annotationId: string;
      content: string;
    }) => updateAnnotation(annotationId, { content }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: [
          "annotations",
          projectId,
          documentId,
          effectiveVersionId,
          pageNumber,
        ],
      });
    },
  });

  useEffect(() => {
    if (!signedUrl.data) return;

    let cancelled = false;
    let loadedPdf: PDFDocumentProxy | null = null;

    async function load() {
      setLoadingPdf(true);
      try {
        const pdfjs = await import("pdfjs-dist");
        pdfjs.GlobalWorkerOptions.workerSrc = new URL(
          "pdfjs-dist/build/pdf.worker.min.mjs",
          import.meta.url,
        ).toString();

        const task = pdfjs.getDocument(signedUrl.data);
        loadedPdf = await task.promise;

        if (!cancelled) {
          setPdf(loadedPdf);
          setPageNumber((current) =>
            Math.min(Math.max(1, current), loadedPdf?.numPages ?? 1),
          );
        }
      } finally {
        if (!cancelled) setLoadingPdf(false);
      }
    }

    void load();

    return () => {
      cancelled = true;
      if (loadedPdf) void loadedPdf.destroy();
    };
  }, [signedUrl.data]);

  useEffect(() => {
    if (!pdf || !canvasRef.current) return;

    let cancelled = false;
    let renderTask: { promise: Promise<unknown>; cancel: () => void } | null = null;
    const canvas = canvasRef.current;

    async function renderPage() {
      const page = await pdf.getPage(pageNumber);
      if (cancelled) return;

      const viewport = page.getViewport({ scale });
      const context = canvas.getContext("2d");
      if (!context) return;

      const outputScale = window.devicePixelRatio || 1;
      canvas.width = Math.floor(viewport.width * outputScale);
      canvas.height = Math.floor(viewport.height * outputScale);
      canvas.style.width = Math.floor(viewport.width) + "px";
      canvas.style.height = Math.floor(viewport.height) + "px";

      const transform =
        outputScale !== 1
          ? ([outputScale, 0, 0, outputScale, 0, 0] as [
              number,
              number,
              number,
              number,
              number,
              number,
            ])
          : undefined;

      renderTask = page.render({
        canvasContext: context,
        viewport,
        transform,
      });
      try {
        await renderTask.promise;
      } catch (error) {
        if (!cancelled && (error as { name?: string })?.name !== "RenderingCancelledException") {
          throw error;
        }
        return;
      }

      const textLayerContainer = textLayerRef.current;
      if (textLayerContainer) {
        textLayerContainer.replaceChildren();
        textLayerContainer.style.setProperty("--scale-factor", String(scale));
        textLayerContainer.style.width = Math.floor(viewport.width) + "px";
        textLayerContainer.style.height = Math.floor(viewport.height) + "px";

        const pdfjs = await import("pdfjs-dist");
        const textLayer = new pdfjs.TextLayer({
          textContentSource: page.streamTextContent(),
          container: textLayerContainer,
          viewport,
        });
        await textLayer.render();
      }
    }

    void renderPage();
    return () => {
      cancelled = true;
      renderTask?.cancel();
    };
  }, [pdf, pageNumber, scale]);

  function pointFromEvent(event: PointerEvent<HTMLDivElement>) {
    const overlay = overlayRef.current;
    if (!overlay) return null;
    const rect = overlay.getBoundingClientRect();
    if (!rect.width || !rect.height) return null;

    return {
      x: Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width)),
      y: Math.min(1, Math.max(0, (event.clientY - rect.top) / rect.height)),
    };
  }

  function onPointerDown(event: PointerEvent<HTMLDivElement>) {
    if (create.isPending) return;
    const point = pointFromEvent(event);
    if (!point) return;
    dragStart.current = point;
    setDraftRect({ x: point.x, y: point.y, width: 0.001, height: 0.001 });
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function onPointerMove(event: PointerEvent<HTMLDivElement>) {
    const start = dragStart.current;
    if (!start) return;
    const point = pointFromEvent(event);
    if (!point) return;

    const x = Math.min(start.x, point.x);
    const y = Math.min(start.y, point.y);
    const width = Math.max(0.001, Math.abs(point.x - start.x));
    const height = Math.max(0.001, Math.abs(point.y - start.y));

    setDraftRect({
      x,
      y,
      width: Math.min(width, 1 - x),
      height: Math.min(height, 1 - y),
    });
  }

  function onPointerUp(event: PointerEvent<HTMLDivElement>) {
    const rect = draftRect;
    dragStart.current = null;

    try {
      event.currentTarget.releasePointerCapture(event.pointerId);
    } catch {
      // Pointer capture may already be released.
    }

    if (!rect || rect.width < 0.01 || rect.height < 0.01) {
      setDraftRect(null);
      return;
    }

    const note = window.prompt("Ghi chú cho vùng highlight này (có thể để trống):");
    create.mutate({
      rectangles: [rect],
      note: note?.trim() || null,
      annotationType: "rectangle",
    });
  }

  function onTextSelectionEnd() {
    if (annotationMode !== "text" || create.isPending) return;

    const selection = window.getSelection();
    const layer = textLayerRef.current;
    if (!selection || selection.isCollapsed || !layer) return;

    const selectedText = selection.toString().trim();
    if (!selectedText) return;

    const range = selection.rangeCount > 0 ? selection.getRangeAt(0) : null;
    if (!range) return;

    const layerRect = layer.getBoundingClientRect();
    if (!layerRect.width || !layerRect.height) return;

    const rectangles: AnnotationRectangle[] = [];
    for (const clientRect of Array.from(range.getClientRects())) {
      const left = Math.max(clientRect.left, layerRect.left);
      const top = Math.max(clientRect.top, layerRect.top);
      const right = Math.min(clientRect.right, layerRect.right);
      const bottom = Math.min(clientRect.bottom, layerRect.bottom);

      if (right <= left || bottom <= top) continue;

      const x = (left - layerRect.left) / layerRect.width;
      const y = (top - layerRect.top) / layerRect.height;
      const width = (right - left) / layerRect.width;
      const height = (bottom - top) / layerRect.height;

      rectangles.push({
        x: Math.min(1, Math.max(0, x)),
        y: Math.min(1, Math.max(0, y)),
        width: Math.min(width, 1 - x),
        height: Math.min(height, 1 - y),
      });
    }

    if (!rectangles.length) return;

    const note = window.prompt(
      "Ghi chú cho đoạn text được highlight (có thể để trống):",
    );
    create.mutate({
      rectangles,
      note: note?.trim() || null,
      annotationType: "text_highlight",
      selectedText,
    });
    selection.removeAllRanges();
  }

  if (detail.isLoading) {
    return <LoadingCard text="Đang tải document..." />;
  }

  if (detail.isError || !detail.data) {
    return (
      <div className="rounded-2xl bg-red-50 p-5 text-sm text-red-700">
        Không tải được document.
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1500px] space-y-5">
      <section className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <div className="font-hand text-2xl text-[#b9634c]">Read, highlight, remember</div>
          <h1 className="font-display text-4xl font-semibold">
            {detail.data.display_name}
          </h1>
          <p className="mt-2 text-sm text-[#7d7167]">
            Annotation được khóa theo đúng document version, không tự remap sang version mới.
          </p>
        </div>

        <div className="flex flex-wrap items-end gap-3">
          <label className="text-xs font-medium text-[#6f6258]">
            Version
            <select
              value={effectiveVersionId}
              onChange={(event) => {
                setSelectedVersionId(event.target.value);
                setPageNumber(1);
                setPdf(null);
              }}
              className="mt-1 block rounded-xl border border-[#755640]/15 bg-white/80 px-3 py-2 text-sm"
            >
              {detail.data.versions.map((version) => (
                <option key={version.id} value={version.id}>
                  v{version.version_number} · {version.status}
                </option>
              ))}
            </select>
          </label>

          <div className="text-xs font-medium text-[#6f6258]">
            Mode
            <div className="mt-1 flex rounded-xl border border-[#755640]/15 bg-white/80 p-1">
              <button
                type="button"
                onClick={() => setAnnotationMode("rectangle")}
                className={
                  "rounded-lg px-3 py-1.5 text-xs font-semibold " +
                  (annotationMode === "rectangle"
                    ? "bg-[#efd3c7] text-[#8f4738]"
                    : "text-[#7d7167]")
                }
              >
                Rectangle
              </button>
              <button
                type="button"
                onClick={() => setAnnotationMode("text")}
                className={
                  "rounded-lg px-3 py-1.5 text-xs font-semibold " +
                  (annotationMode === "text"
                    ? "bg-[#dce6d8] text-[#587052]"
                    : "text-[#7d7167]")
                }
              >
                Text
              </button>
            </div>
          </div>

          <label className="text-xs font-medium text-[#6f6258]">
            Highlight
            <input
              type="color"
              value={color}
              onChange={(event) => setColor(event.target.value.toUpperCase())}
              className="mt-1 block h-10 w-14 rounded-xl border border-[#755640]/15 bg-white p-1"
            />
          </label>

          <label className="text-xs font-medium text-[#6f6258]">
            Zoom
            <select
              value={scale}
              onChange={(event) => setScale(Number(event.target.value))}
              className="mt-1 block rounded-xl border border-[#755640]/15 bg-white/80 px-3 py-2 text-sm"
            >
              <option value={0.8}>80%</option>
              <option value={1}>100%</option>
              <option value={1.25}>125%</option>
              <option value={1.5}>150%</option>
              <option value={2}>200%</option>
            </select>
          </label>
        </div>
      </section>

      {selectedVersion?.mime_type !== "application/pdf" ? (
        <div className="paper-card rounded-[26px] p-8 text-center">
          Viewer annotation hiện hỗ trợ PDF. DOCX vẫn được ingest và dùng cho RAG bình thường.
        </div>
      ) : (
        <section className="grid gap-5 xl:grid-cols-[1fr_320px]">
          <div className="paper-card overflow-hidden rounded-[26px]">
            <div className="flex items-center justify-between border-b border-[#755640]/10 bg-[#fffaf4] px-4 py-3">
              <button
                onClick={() => setPageNumber((page) => Math.max(1, page - 1))}
                disabled={pageNumber <= 1}
                className="grid h-9 w-9 place-items-center rounded-xl border border-[#755640]/12 bg-white/70 disabled:opacity-40"
              >
                <ChevronLeft size={17} />
              </button>

              <div className="flex items-center gap-2 text-sm">
                <span className="font-semibold">Page {pageNumber}</span>
                <span className="text-[#8a7b70]">/ {pdf?.numPages ?? "—"}</span>
              </div>

              <button
                onClick={() =>
                  setPageNumber((page) =>
                    Math.min(pdf?.numPages ?? page, page + 1),
                  )
                }
                disabled={!pdf || pageNumber >= pdf.numPages}
                className="grid h-9 w-9 place-items-center rounded-xl border border-[#755640]/12 bg-white/70 disabled:opacity-40"
              >
                <ChevronRight size={17} />
              </button>
            </div>

            <div className="soft-scrollbar overflow-auto bg-[#e9e2d8] p-5">
              {loadingPdf || signedUrl.isLoading ? (
                <LoadingCard text="Đang mở PDF..." />
              ) : signedUrl.isError ? (
                <div className="rounded-xl bg-red-50 p-4 text-sm text-red-700">
                  Không lấy được signed URL cho file.
                </div>
              ) : (
                <div
                  className="relative mx-auto w-fit shadow-2xl shadow-[#5d493a]/15"
                  onMouseUp={onTextSelectionEnd}
                >
                  <canvas ref={canvasRef} className="block bg-white" />

                  <div
                    ref={textLayerRef}
                    className={
                      "textLayer absolute inset-0 " +
                      (annotationMode === "text"
                        ? "cursor-text select-text"
                        : "pointer-events-none select-none")
                    }
                  />

                  <div
                    className="pointer-events-none absolute inset-0"
                    aria-hidden="true"
                  >
                    {annotations.data?.flatMap((annotation) =>
                      (annotation.rectangles ?? []).map((rect, index) => (
                        <div
                          key={annotation.id + "-" + index}
                          className="absolute border border-black/10"
                          style={{
                            left: rect.x * 100 + "%",
                            top: rect.y * 100 + "%",
                            width: rect.width * 100 + "%",
                            height: rect.height * 100 + "%",
                            backgroundColor: annotation.color + "55",
                          }}
                        />
                      )),
                    )}

                    {draftRect && (
                      <div
                        className="absolute border-2 border-[#9b4d3b]"
                        style={{
                          left: draftRect.x * 100 + "%",
                          top: draftRect.y * 100 + "%",
                          width: draftRect.width * 100 + "%",
                          height: draftRect.height * 100 + "%",
                          backgroundColor: color + "45",
                        }}
                      />
                    )}
                  </div>

                  {annotationMode === "rectangle" && (
                    <div
                      ref={overlayRef}
                      className="absolute inset-0 cursor-crosshair touch-none select-none"
                      onPointerDown={onPointerDown}
                      onPointerMove={onPointerMove}
                      onPointerUp={onPointerUp}
                    />
                  )}
                </div>
              )}
            </div>
          </div>

          <aside className="paper-card h-fit rounded-[26px] p-5 xl:sticky xl:top-28">
            <div className="flex items-center gap-3">
              <div className="grid h-10 w-10 place-items-center rounded-xl bg-[#f3ddd4] text-[#9c513e]">
                <Highlighter size={18} />
              </div>
              <div>
                <h2 className="font-display text-xl font-semibold">Page notes</h2>
                <p className="text-xs text-[#8a7b70]">
                  Rectangle: kéo vùng. Text: bôi đen trực tiếp chữ trên PDF.
                </p>
              </div>
            </div>

            <div className="mt-5 space-y-3">
              {annotations.data?.map((annotation) => (
                <div
                  key={annotation.id}
                  className="rounded-2xl border border-[#755640]/10 bg-white/58 p-4"
                >
                  <div className="flex items-start gap-3">
                    <span
                      className="mt-1 h-4 w-4 shrink-0 rounded"
                      style={{ backgroundColor: annotation.color }}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="text-xs font-semibold uppercase tracking-wide text-[#8a7b70]">
                        {annotation.annotation_type}
                      </div>
                      {annotation.selected_text && (
                        <blockquote className="mt-2 line-clamp-4 border-l-2 border-[#b9634c]/30 pl-2 text-xs leading-5 text-[#6f6258]">
                          {annotation.selected_text}
                        </blockquote>
                      )}
                      <button
                        onClick={() => {
                          const next = window.prompt(
                            "Sửa ghi chú:",
                            annotation.content ?? "",
                          );
                          if (next !== null) {
                            editNote.mutate({
                              annotationId: annotation.id,
                              content: next.trim(),
                            });
                          }
                        }}
                        className="mt-2 w-full text-left text-sm leading-6 text-[#4f443c]"
                      >
                        {annotation.content || "Bấm để thêm ghi chú"}
                      </button>
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
                <div className="rounded-2xl border border-dashed border-[#8b6b53]/20 p-5 text-center text-sm text-[#8a7b70]">
                  <MessageSquareText className="mx-auto mb-2" size={20} />
                  Chưa có annotation ở page này.
                </div>
              )}
            </div>
          </aside>
        </section>
      )}
    </div>
  );
}

function LoadingCard({ text }: { text: string }) {
  return (
    <div className="grid min-h-40 place-items-center">
      <div className="flex items-center gap-2 text-sm text-[#7d7167]">
        <Loader2 size={17} className="animate-spin" />
        {text}
      </div>
    </div>
  );
}
