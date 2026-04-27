/**
 * Lightweight Charts Drawing Tools & Multi-pane UI Manager
 * Supports: Trendlines, Rectangles, Long/Short Positions with Risk/Reward
 */

const props = window.CHART_PROPS || {};
const appContainer = document.getElementById('app-container');
const mainWrapper = document.getElementById('chart');
const toolbar = document.getElementById('toolbar');

// --- Setup Main Chart ---
// Use the existing chart instance created by chart_component.html
const mainChart = window.mainChart;
const mainSeries = window.mainSeries;

if (props.markers && props.markers.length > 0) mainSeries.setMarkers(props.markers);

if (props.ema20) mainChart.addLineSeries({ color: '#2962ff', lineWidth: 2, crosshairMarkerVisible: false }).setData(props.ema20);
if (props.ema50) mainChart.addLineSeries({ color: '#ff9800', lineWidth: 2, crosshairMarkerVisible: false }).setData(props.ema50);

// --- Responsive Resize ---
new ResizeObserver(entries => {
    for (let entry of entries) {
        const target = entry.target;
        mainChart.applyOptions({ width: target.clientWidth, height: target.clientHeight });
    }
}).observe(mainWrapper);
mainChart.timeScale().fitContent();

// ==========================================
// DRAWING TOOLS IMPLEMENTATION
// ==========================================
const canvas = document.createElement('canvas');
canvas.style.position = 'absolute';
canvas.style.top = '0';
canvas.style.left = '0';
canvas.style.pointerEvents = 'none'; // Let chart absorb native events
canvas.style.zIndex = '10';
mainWrapper.appendChild(canvas);
const ctx = canvas.getContext('2d');

const storageKey = `drawings_${props.symbol}_${props.timeframe}`;
let drawings = JSON.parse(localStorage.getItem(storageKey)) || [];
let currentMode = null; 
let isDrawing = false;
let currentShape = null;
let mouseLogical = null;

function syncCanvasSize() {
    canvas.width = mainWrapper.clientWidth;
    canvas.height = mainWrapper.clientHeight;
    renderDrawings();
}
new ResizeObserver(syncCanvasSize).observe(mainWrapper);

const tools = [
    { id: 'cursor', label: '👆 Cursor' },
    { id: 'trendline', label: '📏 Trendline' },
    { id: 'rectangle', label: '🔲 Rectangle' },
    { id: 'long', label: '📈 Long Pos' },
    { id: 'short', label: '📉 Short Pos' },
    { id: 'clear', label: '🗑️ Clear All' }
];

tools.forEach(t => {
    const btn = document.createElement('button');
    btn.innerText = t.label;
    btn.id = `btn-${t.id}`;
    if (t.id === 'cursor') btn.classList.add('active');
    btn.onclick = () => selectTool(t.id, btn);
    toolbar.appendChild(btn);
});

function selectTool(mode, btn) {
    if (mode === 'clear') {
        drawings = [];
        localStorage.removeItem(storageKey);
        renderDrawings();
        return;
    }
    currentMode = mode === 'cursor' ? null : mode;
    isDrawing = false;
    currentShape = null;
    Array.from(toolbar.children).forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    
    mainChart.applyOptions({
        handleScroll: currentMode === null,
        handleScale: currentMode === null
    });
}

mainChart.subscribeCrosshairMove(param => {
    if (!param.time || !param.seriesPrices.get(mainSeries)) {
        mouseLogical = null;
        return;
    }
    mouseLogical = { time: param.time, price: param.seriesPrices.get(mainSeries).close };
    
    if (isDrawing && currentShape) {
        currentShape.p2 = mouseLogical;
        renderDrawings();
    }
});

mainWrapper.addEventListener('mousedown', (e) => {
    if (!currentMode || !mouseLogical) return;
    if (e.button !== 0) return; // Only left click
    
    isDrawing = true;
    currentShape = { type: currentMode, p1: mouseLogical, p2: mouseLogical };
});

mainWrapper.addEventListener('mouseup', (e) => {
    if (!isDrawing || !currentShape) return;
    isDrawing = false;
    
    if (currentShape.p1.time !== currentShape.p2.time || currentShape.p1.price !== currentShape.p2.price) {
        drawings.push(currentShape);
        localStorage.setItem(storageKey, JSON.stringify(drawings));
    }
    currentShape = null;
    renderDrawings();
});

mainChart.timeScale().subscribeVisibleTimeRangeChange(renderDrawings);
mainChart.subscribeCrosshairMove(renderDrawings);

function renderDrawings() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    [...drawings, ...(isDrawing && currentShape ? [currentShape] : [])].forEach(shape => {
        const x1 = mainChart.timeScale().timeToCoordinate(shape.p1.time);
        const y1 = mainSeries.priceToCoordinate(shape.p1.price);
        const x2 = mainChart.timeScale().timeToCoordinate(shape.p2.time);
        const y2 = mainSeries.priceToCoordinate(shape.p2.price);

        if (x1 === null || y1 === null || x2 === null || y2 === null) return;

        ctx.beginPath();
        
        if (shape.type === 'trendline') {
            ctx.moveTo(x1, y1);
            ctx.lineTo(x2, y2);
            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = 2;
            ctx.stroke();
        } 
        else if (shape.type === 'rectangle') {
            ctx.rect(x1, y1, x2 - x1, y2 - y1);
            ctx.fillStyle = 'rgba(41, 98, 255, 0.2)';
            ctx.strokeStyle = 'rgba(41, 98, 255, 1)';
            ctx.lineWidth = 2;
            ctx.fill();
            ctx.stroke();
        } 
        else if (shape.type === 'long' || shape.type === 'short') {
            drawPositionTool(shape, x1, y1, x2, y2);
        }
    });
}

function drawPositionTool(shape, x1, y1, x2, y2) {
    const isLong = shape.type === 'long';
    const entry = shape.p1.price;
    const sl = shape.p2.price;

    if (entry === sl) return; 

    const risk = Math.abs(entry - sl);
    const rr = props.rr_ratio || 2.0; 
    const tp = isLong ? entry + (risk * rr) : entry - (risk * rr);

    const riskPct = (risk / entry) * 100;
    const rewardPct = (Math.abs(tp - entry) / entry) * 100;

    const yEntry = mainSeries.priceToCoordinate(entry);
    const ySL = mainSeries.priceToCoordinate(sl);
    const yTP = mainSeries.priceToCoordinate(tp);

    const width = 140; 
    const tpColor = 'rgba(0, 255, 136, 0.2)';
    const slColor = 'rgba(255, 68, 68, 0.2)';

    ctx.fillStyle = tpColor;
    ctx.fillRect(x1, yTP, width, yEntry - yTP);
    ctx.fillStyle = slColor;
    ctx.fillRect(x1, yEntry, width, ySL - yEntry);

    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x1, yEntry); ctx.lineTo(x1 + width, yEntry); // Entry Midline
    ctx.moveTo(x1, yTP); ctx.lineTo(x1 + width, yTP);       // TP top/bottom
    ctx.moveTo(x1, ySL); ctx.lineTo(x1 + width, ySL);       // SL top/bottom
    ctx.stroke();

    ctx.fillStyle = '#ffffff';
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    
    const tpOffset = (yEntry - yTP) > 0 ? -10 : 10;
    const slOffset = (ySL - yEntry) > 0 ? 10 : -10;

    ctx.fillText(`TP: ${tp.toFixed(4)} (${rewardPct.toFixed(2)}%)`, x1 + 5, yTP - tpOffset);
    ctx.fillText(`Entry: ${entry.toFixed(4)}`, x1 + 5, yEntry - 10);
    ctx.fillText(`RR: ${rr.toFixed(2)}`, x1 + 5, yEntry + 10);
    ctx.fillText(`SL: ${sl.toFixed(4)} (${riskPct.toFixed(2)}%)`, x1 + 5, ySL + slOffset);
}