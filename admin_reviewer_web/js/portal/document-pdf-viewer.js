/**
 * Inline PDF viewer for document review (authorized view-url + PDF.js).
 */
import * as pdfjsLib from 'https://cdn.jsdelivr.net/npm/pdfjs-dist@4.10.38/build/pdf.mjs';

pdfjsLib.GlobalWorkerOptions.workerSrc =
  'https://cdn.jsdelivr.net/npm/pdfjs-dist@4.10.38/build/pdf.worker.min.mjs';

const URL_REFRESH_MS = 4 * 60 * 1000;
const RESIZE_DEBOUNCE_MS = 120;

function isCancelledRenderError(err) {
  if (!err) return false;
  const name = String(err.name || '');
  if (name === 'RenderingCancelledException') return true;
  const msg = String(err.message || err.toString?.() || '');
  return /Rendering cancelled/i.test(msg) || (/\bcancel/i.test(msg) && /\brender/i.test(msg));
}

/**
 * @param {HTMLElement} root Mount point (toolbar + canvas area injected inside).
 * @param {{ documentId: string, fetchViewUrl: () => Promise<{ url: string, expiresInSeconds?: number }> }} opts
 */
export function mountDocumentPdfViewer(root, opts) {
  if (!root) return { destroy() {}, goToPage() {} };

  let destroyed = false;
  let pdfDoc = null;
  let pageNum = 1;
  let scaleMode = 'fit-width';
  let zoomFactor = 1;
  let viewUrl = '';
  let urlFetchedAt = 0;
  /** @type {import('pdfjs-dist').RenderTask | null} */
  let activeRenderTask = null;
  let refreshTimer = null;
  let resizeDebounceId = null;
  let renderGen = 0;
  let renderChain = Promise.resolve();
  let lastObservedWrapWidth = 0;
  let loadGen = 0;

  root.innerHTML = `
    <div class="doc-pdf-viewer">
      <div class="doc-pdf-viewer__toolbar" role="toolbar" aria-label="PDF controls">
        <button type="button" class="btn-ghost btn-sm" data-pdf-prev aria-label="Previous page">‹</button>
        <span class="doc-pdf-viewer__page">
          <input type="number" min="1" data-pdf-page-input aria-label="Page number" class="doc-pdf-viewer__page-input" />
          <span data-pdf-page-total class="muted">/ —</span>
        </span>
        <button type="button" class="btn-ghost btn-sm" data-pdf-next aria-label="Next page">›</button>
        <span class="doc-pdf-viewer__sep"></span>
        <button type="button" class="btn-ghost btn-sm" data-pdf-zoom-out title="Zoom out">−</button>
        <button type="button" class="btn-ghost btn-sm" data-pdf-fit title="Fit width">Fit width</button>
        <button type="button" class="btn-ghost btn-sm" data-pdf-zoom-in title="Zoom in">+</button>
      </div>
      <div class="doc-pdf-viewer__stage">
        <p class="doc-pdf-viewer__status muted" data-pdf-status>Loading document…</p>
        <div class="doc-pdf-viewer__canvas-wrap" data-pdf-canvas-wrap hidden>
          <canvas data-pdf-canvas></canvas>
        </div>
      </div>
      <div class="doc-pdf-viewer__footer">
        <button type="button" class="btn-ghost btn-sm" data-pdf-open-tab>Open in new tab</button>
        <button type="button" class="btn-ghost btn-sm" data-pdf-download>Download</button>
        <button type="button" class="btn-ghost btn-sm" data-pdf-retry hidden>Retry</button>
      </div>
    </div>`;

  const statusEl = root.querySelector('[data-pdf-status]');
  const wrapEl = root.querySelector('[data-pdf-canvas-wrap]');
  const canvas = root.querySelector('[data-pdf-canvas]');
  const ctx = canvas.getContext('2d');
  const pageInput = root.querySelector('[data-pdf-page-input]');
  const pageTotalEl = root.querySelector('[data-pdf-page-total]');
  const retryBtn = root.querySelector('[data-pdf-retry]');

  function setStatus(msg, isError = false) {
    if (!statusEl || destroyed) return;
    statusEl.textContent = msg;
    statusEl.hidden = false;
    statusEl.classList.toggle('doc-pdf-viewer__status--error', isError);
    if (wrapEl) wrapEl.hidden = isError;
  }

  function clearStatus() {
    if (statusEl) statusEl.hidden = true;
    if (wrapEl) wrapEl.hidden = false;
  }

  async function awaitRenderTaskCancel() {
    if (!activeRenderTask) return;
    const task = activeRenderTask;
    activeRenderTask = null;
    try {
      task.cancel();
    } catch {
      /* ignore */
    }
    try {
      await task.promise;
    } catch (e) {
      if (!isCancelledRenderError(e)) throw e;
    }
  }

  async function ensureUrl(force = false) {
    const stale = !viewUrl || Date.now() - urlFetchedAt > URL_REFRESH_MS;
    if (!force && !stale) return viewUrl;
    const data = await opts.fetchViewUrl();
    viewUrl = data.url;
    urlFetchedAt = Date.now();
    return viewUrl;
  }

  function scheduleUrlRefresh() {
    clearTimeout(refreshTimer);
    refreshTimer = setTimeout(() => {
      if (destroyed) return;
      void ensureUrl(true).catch(() => {
        /* Keep showing loaded document; open/download may fail until manual retry. */
      });
    }, URL_REFRESH_MS);
  }

  async function performRender(requestGen) {
    if (destroyed || requestGen !== renderGen || !pdfDoc) return;

    await awaitRenderTaskCancel();
    if (destroyed || requestGen !== renderGen || !pdfDoc) return;

    const page = await pdfDoc.getPage(pageNum);
    if (destroyed || requestGen !== renderGen) return;

    const baseVp = page.getViewport({ scale: 1 });
    let scale = zoomFactor;
    if (scaleMode === 'fit-width' && wrapEl) {
      const w = Math.max(wrapEl.clientWidth - 24, 280);
      scale = (w / baseVp.width) * zoomFactor;
    }
    const viewport = page.getViewport({ scale });

    canvas.width = Math.floor(viewport.width);
    canvas.height = Math.floor(viewport.height);

    if (destroyed || requestGen !== renderGen) return;

    const task = page.render({ canvasContext: ctx, viewport });
    activeRenderTask = task;
    try {
      await task.promise;
    } catch (e) {
      if (isCancelledRenderError(e)) return;
      throw e;
    } finally {
      if (activeRenderTask === task) activeRenderTask = null;
    }

    if (destroyed || requestGen !== renderGen) return;
    pageInput.value = String(pageNum);
    clearStatus();
    retryBtn.hidden = true;
  }

  function queueRender() {
    const requestGen = ++renderGen;
    renderChain = renderChain
      .then(() => performRender(requestGen))
      .catch((e) => {
        if (destroyed || isCancelledRenderError(e)) return;
        setStatus(e?.message || 'Could not render page.', true);
        retryBtn.hidden = false;
      });
    return renderChain;
  }

  async function loadDocument(forceUrl = false) {
    if (destroyed) return;
    const myLoad = ++loadGen;
    setStatus('Loading document…', false);
    if (wrapEl) wrapEl.hidden = true;
    retryBtn.hidden = true;

    try {
      const url = await ensureUrl(forceUrl);
      if (destroyed || myLoad !== loadGen) return;

      const savedPage = pageNum;
      const savedScaleMode = scaleMode;
      const savedZoom = zoomFactor;

      if (pdfDoc) {
        renderGen += 1;
        await awaitRenderTaskCancel();
        try {
          await pdfDoc.destroy();
        } catch {
          /* ignore */
        }
        pdfDoc = null;
      }

      const loadingTask = pdfjsLib.getDocument({ url, withCredentials: false });
      pdfDoc = await loadingTask.promise;
      if (destroyed || myLoad !== loadGen) return;

      pageNum = Math.min(Math.max(savedPage, 1), pdfDoc.numPages);
      scaleMode = savedScaleMode;
      zoomFactor = savedZoom;
      pageInput.max = String(pdfDoc.numPages);
      pageTotalEl.textContent = `/ ${pdfDoc.numPages}`;

      await queueRender();
      if (destroyed || myLoad !== loadGen) return;
      scheduleUrlRefresh();
    } catch (e) {
      if (destroyed || myLoad !== loadGen) return;
      if (isCancelledRenderError(e)) {
        await queueRender();
        return;
      }
      setStatus(e?.message || 'Could not load PDF.', true);
      retryBtn.hidden = false;
    }
  }

  function goToPage(n) {
    if (!pdfDoc || destroyed) return;
    const next = Math.max(1, Math.min(pdfDoc.numPages, Number(n) || 1));
    if (next !== pageNum) pageNum = next;
    queueRender();
  }

  root.querySelector('[data-pdf-prev]')?.addEventListener('click', () => goToPage(pageNum - 1));
  root.querySelector('[data-pdf-next]')?.addEventListener('click', () => goToPage(pageNum + 1));
  pageInput?.addEventListener('change', () => goToPage(pageInput.value));
  root.querySelector('[data-pdf-zoom-in]')?.addEventListener('click', () => {
    scaleMode = 'custom';
    zoomFactor = Math.min(3, zoomFactor + 0.2);
    queueRender();
  });
  root.querySelector('[data-pdf-zoom-out]')?.addEventListener('click', () => {
    scaleMode = 'custom';
    zoomFactor = Math.max(0.4, zoomFactor - 0.2);
    queueRender();
  });
  root.querySelector('[data-pdf-fit]')?.addEventListener('click', () => {
    scaleMode = 'fit-width';
    zoomFactor = 1;
    queueRender();
  });
  root.querySelector('[data-pdf-open-tab]')?.addEventListener('click', async () => {
    try {
      const url = await ensureUrl(true);
      window.open(url, '_blank', 'noopener,noreferrer');
    } catch (e) {
      setStatus(e.message || 'Could not open PDF.', true);
      retryBtn.hidden = false;
    }
  });
  root.querySelector('[data-pdf-download]')?.addEventListener('click', async () => {
    try {
      const url = await ensureUrl(true);
      const a = document.createElement('a');
      a.href = url;
      a.download = opts.documentId || 'document.pdf';
      a.rel = 'noopener';
      a.click();
    } catch (e) {
      setStatus(e.message || 'Could not download PDF.', true);
      retryBtn.hidden = false;
    }
  });
  retryBtn?.addEventListener('click', () => void loadDocument(true));

  const resizeObserver =
    typeof ResizeObserver !== 'undefined'
      ? new ResizeObserver((entries) => {
          if (destroyed || scaleMode !== 'fit-width' || !pdfDoc) return;
          const rect = entries[0]?.contentRect;
          const w = Math.round(rect?.width ?? wrapEl?.clientWidth ?? 0);
          if (w < 8 || w === lastObservedWrapWidth) return;
          lastObservedWrapWidth = w;
          clearTimeout(resizeDebounceId);
          resizeDebounceId = setTimeout(() => {
            if (!destroyed && scaleMode === 'fit-width' && pdfDoc) queueRender();
          }, RESIZE_DEBOUNCE_MS);
        })
      : null;
  if (resizeObserver && wrapEl) resizeObserver.observe(wrapEl);

  void loadDocument();

  return {
    goToPage,
    refresh: () => loadDocument(true),
    destroy() {
      destroyed = true;
      loadGen += 1;
      renderGen += 1;
      clearTimeout(refreshTimer);
      clearTimeout(resizeDebounceId);
      resizeObserver?.disconnect();
      const doc = pdfDoc;
      pdfDoc = null;
      void awaitRenderTaskCancel();
      if (doc) void doc.destroy().catch(() => {});
      root.innerHTML = '';
    },
  };
}
