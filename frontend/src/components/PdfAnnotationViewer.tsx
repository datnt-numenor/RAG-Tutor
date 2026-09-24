"use client";

import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ChevronLeft,
  ChevronRight,
  Highlighter,
  Loader2,
  StickyNote,
  Trash2,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import {
  createAnnotation,
  deleteAnnotation,
  getDocumentSignedUrl,
  listAnnotations,
  updateAnnotation,
  type Annotation,
  type AnnotationRectangle,
} from "@/lib/ragtutor";

type DragState = {
  startX: number;
  startY: number;
  currentX: number;
  currentY: number;
} | null;

export function PdfAnnotationViewer({
  projectId,
  documentId,
  versionId,
}: {
  projectId: string;
  documentId: string;
  versionId: string;
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const overlayRef = useRef<HTMLDivElement | null>(null);
  const renderTaskRef = useRef<{ cancel: () => void } | null>(null);
  const queryClient = useQueryClient();

  const [pdf, setPdf] = useState<any>(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [pageCount, setPageCount] = useState(0);
  const [scale, setScale] = useState(1.25);
  const [drag, setDrag] = useState<DragState>(null);
  const [note, setNote] = useState("");
  const [color, setColor] = useState("#F4D06F");
  const [selectedAnnotation, setSelectedAnnotation] = useState<Annotation | null>(null);

  const signedUrl = useQuery({
    queryKey: ["document-signed-url", versionId],
    queryFn: () => getDocumentSignedUrl(versionId),
    staleTime: 240_000,
  });

  const annotations = useQuery({
    queryKey: ["annotations", projectId, documentId, versionId, pageNumber],
    queryFn: () =>
      listAnnotations(projectId, documentId, versionId, pageNumber),
  });

  useEffect(() => {
    let cancelled = false;

    async function load() {
      if (!signedUrl.data) return;
      const pdfjs = await import("pdfjs-dist");
      pdfjs.GlobalWorkerOptions.workerSrc = new URL(
        "pdfjs-dist/build/pdf.worker.min.mjs",
        import.meta.url,
      ).toString();

      const task = pdfjs.getDocument(signedUrl.data);
      const loaded = await task.promise;
      if (cancelled) return;
      setPdf(loaded);
      setPageCount(loaded.numPages);
      setPageNumber((current) => Math.min(current, loaded.numPages));
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [signedUrl.data]);

  useEffect(() => {
    let cancelled = false;

    async function render() {
      if (!pdf || !canvasRef.current) return;

      renderTaskRef.current?.cancel();
      const page = await pdf.getPage(pageNumber);
      if (cancelled) return;

      const viewport = page.getViewport({ scale });
      const canvas = canvasRef.current;
      const context = canvas.getContext("2d");
      if (!context) return;

      const ratio = window.devicePixelRatio || 1;
      canvas.width = Math.floor(viewport.width * ratio);
      canvas.height = Math.floor(viewport.height * ratio);
      canvas.style.width = viewport.width + "px";
      canvas.style.height = viewport.height + "px";

      const task = page.render({
        canvasContext: context,
        viewport,
        transform: ratio === 1 ? undefined : [ratio, 0, 0, ratio, 0, 0],
      });
      renderTaskRef.current = task;
      try {
        await task.promise;
      } catch (error: any) {
        if (error?.name !== "RenderingCancelledException") throw error;
      }
    }

    void render();
    return () => {
      cancelled = true;
      renderTaskRef.current?.cancel();
    };
  }, [pdf, pageNumber, scale]);

  const create = useMutation({
    mutationFn: async (rectangle: AnnotationRectangle) =>
      createAnnotation(projectId, documentId, versionId, {
        page_number: pageNumber,
        annotation_type: "rectangle",
        rectangles: [rectangle],
        content: note.trim() || null,
        color,
      }),
    onSuccess: async () => {
      setNote("");
      setDrag(null);
      await queryClient.invalidateQueries({
        queryKey: ["annotations", projectId, documentId, versionId, pageNumber],
      });
    },
  });

  const remove = useMutation({
    mutationFn: deleteAnnotation,
    onSuccess: async () => {
      setSelectedAnnotation(null);
      await queryClient.invalidateQueries({
        queryKey: ["annotations", projectId, documentId, versionId, pageNumber],
      });
    },
  });

  const update = useMutation({
    mutationFn: ({
      annotationId,
      content,
    }: {
      annotationId: string;
      content: string;
    }) => updateAnnotation(annotationId, { content }),
    onSuccess: async (updated) => {
      setSelectedAnnotation(updated);
      await queryClient.invalidateQueries({
        queryKey: ["annotations", projectId, documentId, versionId, pageNumber],
      });
    },
  });

  function pointerPosition(event: React.PointerEvent<HTMLDivElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    return {
      x: Math.max(0, Math.min(rect.width, event.clientX - rect.left)),
      y: Math.max(0, Math.min(rect.height, event.clientY - rect.top)),
      width: rect.width,
      height: rect.height,
    };
  }

  function onPointerDown(event: React.PointerEvent<HTMLDivElement>) {
    if (!overlayRef.current || create.isPending) return;
    const p = pointerPosition(event);
    event.currentTarget.setPointerCapture(event.pointerId);
    setSelectedAnnotation(null);
    setDrag({
      startX: p.x,
      startY: p.y,
      currentX: p.x,
      currentY: p.y,
    });
  }

  function onPointerMove(event: React.PointerEvent<HTMLDivElement>) {
    if (!drag) return;
    const p = pointerPosition(event);
    setDrag((current) =>
      current
        ? {
            ...current,
            currentX: p.x,
            currentY: p.y,
          }
        : current,
    );
  }

  function onPointerUp(event: React.PointerEvent<HTMLDivElement>) {
    if (!drag) return;

    const rect = event.currentTarget.getBoundingClientRect();
    const left = Math.min(drag.startX, drag.currentX);
    const top = Math.min(drag.startY, drag.currentY);
    const width = Math.abs(drag.currentX - drag.startX);
    const height = Math.abs(drag.currentY - drag.startY);

    if (width < 8 || height < 8 || rect.width <= 0 || rect.height <= 0) {
      setDrag(null);
      return;
    }

    create.mutate({
      x: left / rect.width,
      y: top / rect.height,
      width: width / rect.width,
      height: height / rect.height,
    });
  }

  const dragStyle = drag
    ? {
        left: Math.min(drag.startX, drag.currentX),
        top: Math.min(drag.startY, drag.currentY),
        width: Math.abs(drag.currentX - drag.startX),
        height: Math.abs(drag.currentY - drag.startY),
      }
    : null;

  return (
    <div className="grid gap-5 xl:grid-cols-[1fr_310px]">
      <section className="paper-card rounded-[26px] p-4 md:p-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPageNumber((p) => Math.max(1, p - 1))}
              disabled={pageNumber <= 1}
              className="grid h-10 w-10 place-items-center rounded-xl border border-[#755640]/12 bg-white/70 disabled:opacity-40"
            >
              <ChevronLeft size={17} />
            </button>
            <div className="rounded-xl bg-white/70 px-4 py-2 text-sm">
              Page {pageNumber}/{pageCount || "…"}
            </div>
            <button
              onClick={() => setPageNumber((p) => Math.min(pageCount, p + 1))}
              disabled={!pageCount || pageNumber >= pageCount}
              className="grid h-10 w-10 place-items-center rounded-xl border border-[#755640]/12 bg-white/70 disabled:opacity-40"
            >
              <ChevronRight size={17} />
            </button>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setScale((s) => Math.max(0.6, Number((s - 0.15).toFixed(2))))}
              className="grid h-10 w-10 place-items-center rounded-xl border border-[#755640]/12 bg-white/70"
            >
              <ZoomOut size={17} />
            </button>
            <div className="w-16 text-center text-xs text-[#7d7167]">
              {Math.round(scale * 100)}%
            </div>
            <button
              onClick={() => setScale((s) => Math.min(2.5, Number((s + 0.15).toFixed(2))))}
              className="grid h-10 w-10 place-items-center rounded-xl border border-[#755640]/12 bg-white/70"
            >
              <ZoomIn size={17} />
            </button>
          </div>
        </div>

        <div className="overflow-auto rounded-2xl bg-[#d8d0c6] p-4">
          <div className="relative mx-auto w-fit select-none shadow-xl">
            <canvas ref={canvasRef} className="block bg-white" />

            <div
              ref={overlayRef}
              onPointerDown={onPointerDown}
              onPointerMove={onPointerMove}
              onPointerUp={onPointerUp}
              className="absolute inset-0 cursor-crosshair touch-none"
            >
              {annotations.data?.flatMap((annotation) =>
                annotation.rectangles.map((rectangle, index) => (
                  <button
                    key={annotation.id + "-" + index}
                    onPointerDown={(event) => event.stopPropagation()}
                    onClick={(event) => {
                      event.stopPropagation();
                      setSelectedAnnotation(annotation);
                    }}
                    title={annotation.content || "Annotation"}
                    className="absolute border-2 transition hover:brightness-95"
                    style={{
                      left: rectangle.x * 100 + "%",
                      top: rectangle.y * 100 + "%",
                      width: rectangle.width * 100 + "%",
                      height: rectangle.height * 100 + "%",
                      backgroundColor: annotation.color + "55",
                      borderColor: annotation.color,
                    }}
                  />
                )),
              )}

              {dragStyle && (
                <div
                  className="pointer-events-none absolute border-2 border-[#b9634c] bg-[#f4d06f]/35"
                  style={dragStyle}
                />
              )}
            </div>
          </div>
        </div>

        {(signedUrl.isLoading || !pdf) && (
          <div className="mt-4 flex items-center gap-2 text-sm text-[#7d7167]">
            <Loader2 size={16} className="animate-spin" />
            Đang tải PDF...
          </div>
        )}
      </section>

      <aside className="space-y-4">
        <section className="paper-card rounded-[24px] p-5">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-xl bg-[#f5e3c3] text-[#9d6a28]">
              <Highlighter size={18} />
            </div>
            <div>
              <h2 className="font-display text-xl font-semibold">Annotation</h2>
              <p className="text-xs text-[#8a7b70]">Kéo chuột trên trang để đánh dấu vùng.</p>
            </div>
          </div>

          <label className="mt-5 block text-sm font-medium text-[#62564d]">
            Màu
            <input
              type="color"
              value={color}
              onChange={(e) => setColor(e.target.value.toUpperCase())}
              className="mt-2 h-10 w-full cursor-pointer rounded-xl border border-[#755640]/10 bg-white"
            />
          </label>

          <label className="mt-4 block text-sm font-medium text-[#62564d]">
            Ghi chú cho vùng tiếp theo
            <textarea
              rows={4}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Ví dụ: định nghĩa quan trọng..."
              className="mt-2 w-full resize-y rounded-2xl border border-[#755640]/12 bg-white/70 p-3 text-sm outline-none focus:border-[#b9634c]/35"
            />
          </label>
        </section>

        <section className="paper-card rounded-[24px] p-5">
          <div className="flex items-center gap-2">
            <StickyNote size={18} className="text-[#b9634c]" />
            <h2 className="font-display text-xl font-semibold">Page notes</h2>
          </div>

          <div className="mt-4 space-y-3">
            {annotations.data?.map((annotation) => (
              <button
                key={annotation.id}
                onClick={() => setSelectedAnnotation(annotation)}
                className={
                  "w-full rounded-2xl border p-3 text-left transition " +
                  (selectedAnnotation?.id === annotation.id
                    ? "border-[#b9634c]/30 bg-[#f6e3da]"
                    : "border-[#755640]/9 bg-white/55 hover:bg-white/80")
                }
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-semibold uppercase tracking-wide text-[#8a7b70]">
                    {annotation.annotation_type}
                  </span>
                  <span
                    className="h-4 w-4 rounded-full border border-black/10"
                    style={{ backgroundColor: annotation.color }}
                  />
                </div>
                <p className="mt-2 line-clamp-3 text-sm leading-5 text-[#5f534a]">
                  {annotation.content || "Không có ghi chú."}
                </p>
              </button>
            ))}

            {!annotations.isLoading && !annotations.data?.length && (
              <div className="rounded-2xl bg-white/45 p-4 text-sm text-[#8a7b70]">
                Trang này chưa có annotation.
              </div>
            )}
          </div>
        </section>

        {selectedAnnotation && (
          <section className="paper-card rounded-[24px] p-5">
            <div className="mb-3 text-sm font-semibold">Chỉnh ghi chú</div>
            <textarea
              key={selectedAnnotation.id + selectedAnnotation.updated_at}
              rows={4}
              defaultValue={selectedAnnotation.content ?? ""}
              onBlur={(e) => {
                const value = e.currentTarget.value;
                if (value !== (selectedAnnotation.content ?? "")) {
                  update.mutate({
                    annotationId: selectedAnnotation.id,
                    content: value,
                  });
                }
              }}
              className="w-full resize-y rounded-2xl border border-[#755640]/12 bg-white/70 p-3 text-sm outline-none"
            />

            <button
              onClick={() => {
                if (window.confirm("Xóa annotation này?")) {
                  remove.mutate(selectedAnnotation.id);
                }
              }}
              className="mt-3 inline-flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-2 text-sm font-semibold text-red-700"
            >
              <Trash2 size={15} />
              Xóa annotation
            </button>
          </section>
        )}
      </aside>
    </div>
  );
}
