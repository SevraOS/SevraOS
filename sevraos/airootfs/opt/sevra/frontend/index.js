// SevraOS Patient Terminal Application Logic - Figma Pixel-Perfect Mappings

document.addEventListener('DOMContentLoaded', () => {
    
    // Elements Selection
    const sidebar = document.querySelector('.sidebar');
    const sidebarMenuToggle = document.getElementById('sidebarMenuToggle');
    const navItems = document.querySelectorAll('.nav-item');
    const pagePanels = document.querySelectorAll('.page-panel');
    
    const themeBtnLight = document.getElementById('themeBtnLight');
    const themeBtnDark = document.getElementById('themeBtnDark');
    
    const btnEndCase = document.getElementById('btnEndCase');
    const patientCaseModal = document.getElementById('patientCaseModal');
    const btnCancelEndCase = document.getElementById('btnCancelEndCase');
    const btnConfirmEndCase = document.getElementById('btnConfirmEndCase');
    
    // State Variables
    let currentTheme = 'dark';
    let ws = null;
    let isLocked = false;
    let lastActiveTime = Date.now();
    let activeTrends = {
        hr: true,
        bp: true,
        spo2: true
    };
    
    // Vitals Seed Values (from Figma)
    let currentVitals = {
        hr: 105,
        bp: "160/95",
        temp: 35.8,
        spo2: 97,
        glucose: 6.8
    };

    // 1. SIDEBAR EXPAND & NAVIGATION
    sidebarMenuToggle.addEventListener('click', () => {
        sidebar.classList.toggle('expanded');
        if (sidebar.classList.contains('expanded')) {
            sidebar.style.width = 'var(--sidebar-expanded-width)';
            document.querySelectorAll('.nav-label').forEach(lbl => lbl.style.display = 'block');
            document.querySelector('.app-container').style.gridTemplateColumns = 'var(--sidebar-expanded-width) 1fr';
        } else {
            sidebar.style.width = 'var(--sidebar-width)';
            document.querySelectorAll('.nav-label').forEach(lbl => lbl.style.display = 'none');
            document.querySelector('.app-container').style.gridTemplateColumns = 'var(--sidebar-width) 1fr';
        }
    });

    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            if (isLocked) {
                e.preventDefault();
                e.stopPropagation();
                return;
            }
            if (item.classList.contains('logout-btn')) return;
            
            navItems.forEach(nav => nav.classList.remove('active'));
            item.classList.add('active');
            
            const targetPage = item.getAttribute('data-page');
            pagePanels.forEach(panel => {
                panel.classList.remove('active');
                if (panel.id === `page-${targetPage}`) {
                    panel.classList.add('active');
                }
            });
            
            window.dispatchEvent(new Event('resize'));
        });
    });

    // 2. THEME ENGINE
    function setTheme(theme) {
        currentTheme = theme;
        if (theme === 'light') {
            document.body.classList.add('light-mode');
            document.body.classList.remove('dark-mode');
            themeBtnLight.classList.add('active');
            themeBtnDark.classList.remove('active');
        } else {
            document.body.classList.add('dark-mode');
            document.body.classList.remove('light-mode');
            themeBtnDark.classList.add('active');
            themeBtnLight.classList.remove('active');
        }
        drawDashboardTelemetry();
        drawStaticCharts();
    }

    themeBtnLight.addEventListener('click', () => setTheme('light'));
    themeBtnDark.addEventListener('click', () => setTheme('dark'));
    
    document.getElementById('btnSettingsLogout')?.addEventListener('click', () => {
        alert("Logging out from Patient Terminal...");
    });
    document.getElementById('logoutBtn')?.addEventListener('click', () => {
        alert("Logging out from Patient Terminal...");
    });

    // 3. CASE MANAGEMENT MODAL
    btnEndCase.addEventListener('click', () => {
        patientCaseModal.classList.add('active');
    });
    btnCancelEndCase.addEventListener('click', () => {
        patientCaseModal.classList.remove('active');
    });
    btnConfirmEndCase.addEventListener('click', () => {
        patientCaseModal.classList.remove('active');
        alert("Patient Case ended. Resetting terminal environment.");
    });

    // 4. PIXEL-PERFECT DASHBOARD VITALS CHART (FIGMA VALUE ALIGNMENT)
    const dashCanvas = document.getElementById('dashboardTelemetryCanvas');
    const dashCtx = dashCanvas.getContext('2d');
    
    function resizeDashboardCanvas() {
        const rect = dashCanvas.parentElement.getBoundingClientRect();
        dashCanvas.width = rect.width;
        dashCanvas.height = rect.height;
        drawDashboardTelemetry();
    }
    window.addEventListener('resize', resizeDashboardCanvas);

    // Exact data curves from Figma design
    const figmaHRPoints = [
        { val: "120", yPct: 0.35 },
        { val: "130", yPct: 0.22 },
        { val: "136", yPct: 0.16 },
        { val: "128", yPct: 0.24 }
    ];

    const figmaBPPoints = [
        { val: "140/90", yPct: 0.52 },
        { val: "150/100", yPct: 0.46 },
        { val: "125/82", yPct: 0.58 },
        { val: "120/80", yPct: 0.64 }
    ];

    const figmaSpO2Points = [
        { val: "95", yPct: 0.78 },
        { val: "92", yPct: 0.84 },
        { val: "96", yPct: 0.76 },
        { val: "97", yPct: 0.72 }
    ];

    function drawPillBadge(ctx, text, x, y, color) {
        ctx.font = "bold 9px 'Outfit', sans-serif";
        const txtWidth = ctx.measureText(text).width;
        const padX = 6;
        const padY = 3;
        const w = txtWidth + padX * 2;
        const h = 12 + padY * 2;
        const rx = x - w/2;
        const ry = y - h - 8; // draw above point

        // Draw pill card background
        ctx.fillStyle = color;
        ctx.beginPath();
        if (ctx.roundRect) {
            ctx.roundRect(rx, ry, w, h, 6);
        } else {
            ctx.rect(rx, ry, w, h);
        }
        ctx.fill();

        // Draw white text
        ctx.fillStyle = "#ffffff";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(text, x, ry + h/2);
    }

    function drawDashboardTelemetry() {
        if (!dashCanvas) return;
        
        const w = dashCanvas.width;
        const h = dashCanvas.height;
        
        dashCtx.clearRect(0, 0, w, h);
        
        // Grid lines
        dashCtx.strokeStyle = currentTheme === 'dark' ? 'rgba(255, 255, 255, 0.04)' : 'rgba(0, 0, 0, 0.04)';
        dashCtx.lineWidth = 1;
        
        const verticalGrids = 12;
        for (let i = 0; i < verticalGrids; i++) {
            const x = (w / (verticalGrids - 1)) * i;
            dashCtx.beginPath();
            dashCtx.moveTo(x, 0);
            dashCtx.lineTo(x, h);
            dashCtx.stroke();
        }
        
        const horizontalGrids = 6;
        for (let i = 0; i < horizontalGrids; i++) {
            const y = (h / (horizontalGrids - 1)) * i;
            dashCtx.beginPath();
            dashCtx.moveTo(0, y);
            dashCtx.lineTo(w, y);
            dashCtx.stroke();
        }

        const colorGreen = '#00e676';
        const colorRed = '#ff1744';
        const colorCyan = '#00e5ff';

        // Curve plotting function
        function plotLine(pts, strokeColor, shadowColor) {
            dashCtx.beginPath();
            dashCtx.strokeStyle = strokeColor;
            dashCtx.lineWidth = 2.5;
            dashCtx.shadowColor = shadowColor;
            dashCtx.shadowBlur = currentTheme === 'dark' ? 8 : 0;

            const xSteps = [w * 0.15, w * 0.40, w * 0.65, w * 0.90];

            for (let i = 0; i < pts.length; i++) {
                const x = xSteps[i];
                const y = pts[i].yPct * h;
                if (i === 0) dashCtx.moveTo(x, y);
                else dashCtx.lineTo(x, y);
            }
            dashCtx.stroke();
            dashCtx.shadowBlur = 0;

            // Draw vertex circles & badges
            for (let i = 0; i < pts.length; i++) {
                const x = xSteps[i];
                const y = pts[i].yPct * h;
                
                // Circle point
                dashCtx.beginPath();
                dashCtx.arc(x, y, 4, 0, Math.PI * 2);
                dashCtx.fillStyle = strokeColor;
                dashCtx.fill();
                
                // Capsule badge above
                drawPillBadge(dashCtx, pts[i].val, x, y, strokeColor);
            }
        }

        // Draw the 3 lines from Figma based on active trends filters
        if (activeTrends.hr) plotLine(figmaHRPoints, colorGreen, 'rgba(0, 230, 118, 0.4)');
        if (activeTrends.bp) plotLine(figmaBPPoints, colorRed, 'rgba(255, 23, 68, 0.4)');
        if (activeTrends.spo2) plotLine(figmaSpO2Points, colorCyan, 'rgba(0, 229, 255, 0.4)');
    }

    // 5. LIVE VITALS BED MONITOR SCROLLING WAVEFORMS
    const ecgCanvas = document.getElementById('liveECGCanvas');
    const ecgCtx = ecgCanvas.getContext('2d');
    const spo2Canvas = document.getElementById('liveSpO2Canvas');
    const spo2Ctx = spo2Canvas.getContext('2d');
    
    let ecgW, ecgH, spo2W, spo2H;
    let ecgX = 0, spo2X = 0;
    
    function resizeLiveCanvases() {
        if (!ecgCanvas || !spo2Canvas) return;
        const ecgRect = ecgCanvas.parentElement.getBoundingClientRect();
        ecgCanvas.width = ecgRect.width;
        ecgCanvas.height = ecgRect.height;
        ecgW = ecgCanvas.width;
        ecgH = ecgCanvas.height;

        const spo2Rect = spo2Canvas.parentElement.getBoundingClientRect();
        spo2Canvas.width = spo2Rect.width;
        spo2Canvas.height = spo2Rect.height;
        spo2W = spo2Canvas.width;
        spo2H = spo2Canvas.height;
        
        ecgCtx.fillStyle = '#000000';
        ecgCtx.fillRect(0, 0, ecgW, ecgH);
        spo2Ctx.fillStyle = '#000000';
        spo2Ctx.fillRect(0, 0, spo2W, spo2H);
    }
    window.addEventListener('resize', resizeLiveCanvases);

    let ecgIndex = 0;
    const ecgPattern = [
        0, 0, 0, 0, 0, 0.05, 0.1, 0.05, 0, 0, // P Wave
        -0.05, 0.9, -0.25, 0,                 // QRS Complex
        0, 0, 0.15, 0.25, 0.15, 0.05, 0, 0, 0, 0 // T Wave
    ];
    
    function getECGValue() {
        ecgIndex++;
        const cycleLength = Math.floor(3600 / currentVitals.hr);
        const idx = ecgIndex % cycleLength;
        if (idx < ecgPattern.length) {
            return ecgPattern[idx] * 0.7;
        }
        return 0;
    }

    let spo2Index = 0;
    function getSpO2Value() {
        spo2Index++;
        const cycleLength = Math.floor(3600 / currentVitals.hr);
        const progress = (spo2Index % cycleLength) / cycleLength;
        
        let val = Math.sin(progress * Math.PI) * 0.6;
        if (progress > 0.4 && progress < 0.6) {
            val += Math.sin((progress - 0.4) * 5 * Math.PI) * 0.1;
        }
        return val * 0.7;
    }

    function scrollWaveforms() {
        if (!ecgCanvas || !spo2Canvas) return;
        
        // Draw scrolling trace on ECG
        const ecgVal = getECGValue();
        const ecgY = ecgH / 2 - ecgVal * (ecgH * 0.4);
        
        ecgCtx.fillStyle = '#000000';
        ecgCtx.fillRect(ecgX, 0, 10, ecgH);
        
        ecgCtx.strokeStyle = '#ff1744';
        ecgCtx.lineWidth = 2.5;
        ecgCtx.beginPath();
        ecgCtx.moveTo(ecgX - 1, lastEcgY);
        ecgCtx.lineTo(ecgX, ecgY);
        ecgCtx.stroke();
        lastEcgY = ecgY;
        
        ecgX = (ecgX + 2) % ecgW;

        // Draw scrolling trace on SpO2
        const spo2Val = getSpO2Value();
        const sY = spo2H / 2 - spo2Val * (spo2H * 0.4);
        
        spo2Ctx.fillStyle = '#000000';
        spo2Ctx.fillRect(spo2X, 0, 10, spo2H);
        
        spo2Ctx.strokeStyle = '#00e5ff';
        spo2Ctx.lineWidth = 2.5;
        spo2Ctx.beginPath();
        spo2Ctx.moveTo(spo2X - 1, lastSpo2Y);
        spo2Ctx.lineTo(spo2X, sY);
        spo2Ctx.stroke();
        lastSpo2Y = sY;
        
        spo2X = (spo2X + 2) % spo2W;
    }
    
    let lastEcgY = ecgH / 2;
    let lastSpo2Y = spo2H / 2;

    // 6. STATIC CHARTS (Risk predictions, sparklines, CT scans)
    const riskCanvas = document.getElementById('riskPredictionCanvas');
    const sparkCanvas = document.getElementById('gaugeSparklineCanvas');
    const prevScanCanvas = document.getElementById('prevScanCanvas');
    const currScanCanvas = document.getElementById('currScanCanvas');

    function drawStaticCharts() {
        // Risk Chart (Bottom Left)
        if (riskCanvas) {
            const rc = riskCanvas.getContext('2d');
            const rw = riskCanvas.parentElement.clientWidth;
            const rh = riskCanvas.parentElement.clientHeight;
            riskCanvas.width = rw;
            riskCanvas.height = rh;
            
            rc.clearRect(0, 0, rw, rh);
            rc.strokeStyle = currentTheme === 'dark' ? 'rgba(255, 255, 255, 0.04)' : 'rgba(0, 0, 0, 0.04)';
            rc.lineWidth = 1;
            rc.beginPath();
            rc.moveTo(0, rh * 0.25); rc.lineTo(rw, rh * 0.25);
            rc.moveTo(0, rh * 0.5); rc.lineTo(rw, rh * 0.5);
            rc.moveTo(0, rh * 0.75); rc.lineTo(rw, rh * 0.75);
            rc.stroke();
            
            const riskPoints = [15, 25, 20, 32, 45, 52, 48, 62, 72];
            const step = rw / (riskPoints.length - 1);
            
            const grad = rc.createLinearGradient(0, 0, 0, rh);
            grad.addColorStop(0, 'rgba(255, 23, 68, 0.2)');
            grad.addColorStop(1, 'rgba(255, 23, 68, 0.0)');
            
            rc.beginPath();
            rc.moveTo(0, rh);
            for(let i=0; i < riskPoints.length; i++) {
                rc.lineTo(i * step, rh - (riskPoints[i]/100) * rh);
            }
            rc.lineTo(rw, rh);
            rc.fillStyle = grad;
            rc.fill();

            rc.beginPath();
            rc.strokeStyle = '#ff1744';
            rc.lineWidth = 2.5;
            for(let i=0; i < riskPoints.length; i++) {
                const x = i * step;
                const y = rh - (riskPoints[i]/100) * rh;
                if (i === 0) rc.moveTo(x, y);
                else rc.lineTo(x, y);
            }
            rc.stroke();
            
            const lastX = rw;
            const lastY = rh - (72/100) * rh;
            rc.beginPath();
            rc.arc(lastX - 2, lastY, 4, 0, Math.PI * 2);
            rc.fillStyle = '#ff1744';
            rc.fill();
            
            rc.beginPath();
            rc.strokeStyle = 'rgba(255, 23, 68, 0.4)';
            rc.setLineDash([4, 4]);
            rc.moveTo(lastX - 2, lastY);
            rc.lineTo(lastX - 2, rh);
            rc.stroke();
            rc.setLineDash([]);
        }

        // Sparkline mini
        if (sparkCanvas) {
            const sc = sparkCanvas.getContext('2d');
            sparkCanvas.width = 60;
            sparkCanvas.height = 24;
            sc.clearRect(0, 0, 60, 24);
            sc.beginPath();
            sc.strokeStyle = '#ffd600';
            sc.lineWidth = 2;
            const sparkPts = [18, 22, 21, 25, 24, 22, 22];
            const sStep = 60 / (sparkPts.length - 1);
            for(let i=0; i < sparkPts.length; i++) {
                const x = i * sStep;
                const y = 24 - (sparkPts[i] / 40) * 20 - 2;
                if (i === 0) sc.moveTo(x, y);
                else sc.lineTo(x, y);
            }
            sc.stroke();
            
            sc.beginPath();
            sc.arc(60 - 2, 24 - (22 / 40) * 20 - 2, 2.5, 0, Math.PI*2);
            sc.fillStyle = '#ffd600';
            sc.fill();
        }

        drawBrainScan(prevScanCanvas, 'left');
        drawBrainScan(currScanCanvas, 'right');
    }

    function drawBrainScan(canvas, type) {
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        canvas.width = 360;
        canvas.height = 290;
        const w = 360;
        const h = 290;
        
        ctx.fillStyle = '#05070a';
        ctx.fillRect(0, 0, w, h);
        
        // Skull Outline
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.85)';
        ctx.lineWidth = 5;
        ctx.beginPath();
        ctx.ellipse(w/2, h/2 - 10, 75, 95, 0, 0, Math.PI * 2);
        ctx.stroke();
        
        // Inner border
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.ellipse(w/2, h/2 - 10, 70, 88, 0, 0, Math.PI * 2);
        ctx.stroke();
        
        // Brain Lobes / Ventricles
        ctx.fillStyle = 'rgba(255, 255, 255, 0.12)';
        ctx.beginPath();
        ctx.ellipse(w/2 - 15, h/2 - 10, 18, 40, 0.1, 0, Math.PI * 2);
        ctx.ellipse(w/2 + 15, h/2 - 10, 18, 40, -0.1, 0, Math.PI * 2);
        ctx.fill();

        // Rib lines
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.06)';
        ctx.lineWidth = 2.5;
        for (let i = -50; i <= 50; i += 25) {
            ctx.beginPath();
            ctx.ellipse(w/2 + i, h/2 - 10, 8, 55, i * 0.005, 0, Math.PI * 2);
            ctx.stroke();
        }

        // Anomaly / lesion
        if (type === 'left') {
            ctx.fillStyle = 'rgba(255, 23, 68, 0.45)';
            ctx.beginPath();
            ctx.arc(w/2 - 30, h/2 + 15, 16, 0, Math.PI*2);
            ctx.fill();
            
            ctx.strokeStyle = 'rgba(255, 23, 68, 0.7)';
            ctx.lineWidth = 1.5;
            ctx.setLineDash([3, 3]);
            ctx.beginPath();
            ctx.arc(w/2 - 30, h/2 + 15, 22, 0, Math.PI*2);
            ctx.stroke();
            ctx.setLineDash([]);
        } else {
            ctx.fillStyle = 'rgba(0, 230, 118, 0.45)';
            ctx.beginPath();
            ctx.arc(w/2 - 30, h/2 + 15, 6, 0, Math.PI*2);
            ctx.fill();
            
            ctx.strokeStyle = 'rgba(0, 230, 118, 0.7)';
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            ctx.arc(w/2 - 30, h/2 + 15, 10, 0, Math.PI*2);
            ctx.stroke();
        }
    }

    // 7. COMPARISON SLIDER DRAG LOGIC
    const comparisonSlider = document.getElementById('scanComparisonSlider');
    const sliderHandle = document.getElementById('sliderHandle');
    const rightClip = document.getElementById('currentScanClipContainer');

    if (comparisonSlider && sliderHandle && rightClip) {
        let activeDrag = false;
        
        function updateSlider(clientX) {
            const rect = comparisonSlider.getBoundingClientRect();
            const x = Math.max(0, Math.min(clientX - rect.left, rect.width));
            const percentage = (x / rect.width) * 100;
            
            sliderHandle.style.left = `${percentage}%`;
            rightClip.style.width = `${100 - percentage}%`;
        }

        sliderHandle.addEventListener('mousedown', (e) => {
            activeDrag = true;
            e.preventDefault();
        });
        window.addEventListener('mouseup', () => { activeDrag = false; });
        window.addEventListener('mousemove', (e) => {
            if (!activeDrag) return;
            updateSlider(e.clientX);
        });

        sliderHandle.addEventListener('touchstart', () => { activeDrag = true; });
        window.addEventListener('touchend', () => { activeDrag = false; });
        window.addEventListener('touchmove', (e) => {
            if (!activeDrag) return;
            updateSlider(e.touches[0].clientX);
        });
        
        rightClip.style.width = '50%';
        sliderHandle.style.left = '50%';
    }

    // 8. DATA POPULATION
    const timelineData = [
        { time: '09:30 AM', title: 'Medication', sub: 'Pill Ingested', icon: 'pill', status: 'completed' },
        { time: '10:00 AM', title: 'Vitals Stable', sub: 'Normative limits', icon: 'check', status: 'completed' },
        { time: '10:30 AM', title: 'HR Rising', sub: 'Spike 120 bpm', icon: 'favorite_border', status: 'completed' },
        { time: '11:00 AM', title: 'Emergency Alert', sub: 'BP critical peak', icon: 'warning', status: 'active-step' },
        { time: '11:30 AM', title: 'Doctor Review', sub: 'Treatment modified', icon: 'clinical_notes', status: 'pending' },
        { time: '12:00 PM', title: 'BP Stable', sub: 'Normative limits', icon: 'check', status: 'pending' }
    ];

    function populateTimeline() {
        const stepsContainer = document.getElementById('timelineSteps');
        if (!stepsContainer) return;
        
        stepsContainer.innerHTML = '';
        timelineData.forEach(item => {
            const step = document.createElement('div');
            step.className = `timeline-step ${item.status}`;
            
            let iconName = 'check';
            if (item.icon === 'pill') iconName = 'medical_services';
            if (item.icon === 'warning') iconName = 'warning';
            if (item.icon === 'favorite_border') iconName = 'ecg';
            if (item.icon === 'clinical_notes') iconName = 'psychology';
            
            step.innerHTML = `
                <div class="timeline-dot">
                    <span class="material-symbols-outlined" style="font-size: 0.75rem;">${iconName}</span>
                </div>
                <div class="timeline-badge">
                    <span class="timeline-badge-title">${item.title}</span>
                    <span class="timeline-badge-sub">${item.sub}</span>
                </div>
                <span class="timeline-time">${item.time}</span>
            `;
            stepsContainer.appendChild(step);
        });
    }

    const medsData = [
        { name: 'Paracetamol', dose: '650mg', route: 'Oral', freq: 'Every 6 hrs', status: 'Active', next: 'In 2 hrs 15 mins', val: 60, time: '10:00 AM' },
        { name: 'Insulin', dose: 'Variable', route: 'SC', freq: 'Before Meals', status: 'Active', next: 'In 1 hrs 45 mins', val: 30, time: '12:00 PM' },
        { name: 'Pantoprazole', dose: '40mg', route: 'IV', freq: 'Once Daily', status: 'Active', next: 'In 30 mins', val: 10, time: '07:00 AM' },
        { name: 'Enoxaparin', dose: '40mg', route: 'SC', freq: 'Once Daily', status: 'Active', next: 'In 5 hrs 10 mins', val: 70, time: '09:00 AM' },
        { name: 'Nebulization', dose: '2.5mg', route: 'Neb', freq: 'Every 6 hrs', status: 'Active', next: 'In 20 mins', val: 90, time: '11:00 AM' },
        { name: 'Normal Saline', dose: '75ml/hr', route: 'IV', freq: 'Infusion Continuous', status: 'Running', next: 'In 2 hrs 30 mins', val: 42, time: 'Live' }
    ];

    function populateMedications() {
        const tableBody = document.querySelector('#medicationsTable tbody');
        if (!tableBody) return;
        
        tableBody.innerHTML = '';
        medsData.forEach(med => {
            const tr = document.createElement('tr');
            
            const r = 9;
            const c = Math.PI * 2 * r;
            const offset = c - (med.val / 100) * c;
            
            tr.innerHTML = `
                <td><strong>${med.name}</strong></td>
                <td>${med.dose}</td>
                <td>${med.route}</td>
                <td>${med.freq}</td>
                <td>
                    <span class="status-dot-text"><span class="dot-green"></span>${med.status}</span>
                </td>
                <td>
                    <div class="progress-ring-cell">
                        <svg class="progress-ring-svg" width="24" height="24">
                            <circle class="progress-ring-circle-bg" cx="12" cy="12" r="${r}" stroke-width="2.2"></circle>
                            <circle class="progress-ring-circle-fill" cx="12" cy="12" r="${r}" stroke-width="2.2" 
                                    stroke-dasharray="${c}" stroke-dashoffset="${offset}"></circle>
                        </svg>
                        <span>${med.next}</span>
                    </div>
                </td>
                <td>${med.time}</td>
            `;
            tableBody.appendChild(tr);
        });
    }

    const reportsData = [
        { name: 'CBC', type: 'LAB', date: '19.05.26 | 8:00', result: 'ABNORMAL', status: 'COMPLETE', isSelected: false },
        { name: 'CRP', type: 'LAB', date: '19.05.25 | 13:00', result: '8 mg/L', status: 'COMPLETE', isSelected: false },
        { name: 'CT BRAIN', type: 'IMAGING', date: '20.05.25 | 9:00', result: 'Review', status: 'Pending', isSelected: true },
        { name: 'X RAY CHEST', type: 'IMAGING', date: '20.05.25 | 15:00', result: 'Improving', status: 'COMPLETE', isSelected: false },
        { name: 'MRI BRAIN', type: 'IMAGING', date: '20.05.25 | 16:00', result: 'Normal', status: 'COMPLETE', isSelected: false },
        { name: 'USG ABDOMEN', type: 'IMAGING', date: '21.05.25 | 7:00', result: 'Review', status: 'COMPLETE', isSelected: false },
        { name: 'PROCALCITONIN', type: 'LAB', date: '21.05.25 | 10:00', result: '0.35 ng/ml', status: 'COMPLETE', isSelected: false },
        { name: 'ECHO', type: 'IMAGING', date: '21.05.25 | 13:00', result: 'NORMAL', status: 'COMPLETE', isSelected: false }
    ];

    function populateReports(filter = 'ALL') {
        const tableBody = document.querySelector('#reportsTable tbody');
        if (!tableBody) return;
        
        tableBody.innerHTML = '';
        reportsData.forEach(rep => {
            if (filter !== 'ALL' && rep.type !== filter) {
                if (filter === 'LAB REPORTS' && rep.type !== 'LAB') return;
                if (filter !== 'LAB REPORTS') return;
            }
            
            const tr = document.createElement('tr');
            if (rep.isSelected) tr.className = 'selected-row';
            
            let resStyle = 'color: var(--color-spo2); font-weight: 700;';
            if (rep.result === 'ABNORMAL') resStyle = 'color: var(--color-bp); font-weight: 700;';
            if (rep.result === 'Review') resStyle = 'color: var(--color-hr); font-weight: 700;';
            
            let statVal = rep.status.toUpperCase();
            
            tr.innerHTML = `
                <td><strong>${rep.name}</strong></td>
                <td>${rep.type}</td>
                <td>${rep.date}</td>
                <td><span style="${resStyle}">${rep.result}</span></td>
                <td>
                    <span class="status-dot-text"><span class="dot-green" style="background-color: ${rep.status === 'Pending' ? 'var(--color-hr)' : 'var(--color-spo2)'}; box-shadow: 0 0 6px ${rep.status === 'Pending' ? 'var(--color-hr)' : 'var(--color-spo2)'};"></span>${statVal}</span>
                </td>
                <td>
                    <button class="btn-view-report"><span class="material-symbols-outlined">visibility</span></button>
                </td>
            `;
            
            tr.addEventListener('click', () => {
                document.querySelectorAll('#reportsTable tbody tr').forEach(row => row.classList.remove('selected-row'));
                tr.classList.add('selected-row');
                
                if (rep.name.includes('BRAIN') || rep.name.includes('CT')) {
                    drawBrainScan(prevScanCanvas, 'left');
                    drawBrainScan(currScanCanvas, 'right');
                } else {
                    drawGenericScan(prevScanCanvas);
                    drawGenericScan(currScanCanvas);
                }
            });
            
            tableBody.appendChild(tr);
        });
    }

    const filterBtns = document.querySelectorAll('#reportFilters button');
    filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            filterBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            populateReports(btn.getAttribute('data-filter'));
        });
    });

    const logsData = [
        { time: '11:05:22 AM', msg: 'ECG Monitor Connected successfully.', status: 'success' },
        { time: '11:05:25 AM', msg: 'Infusion Pump connected to gateway port A3.', status: 'success' },
        { time: '11:08:44 AM', msg: 'NIBP Monitor completed automatic cycle capture.', status: 'success' },
        { time: '11:15:02 AM', msg: 'SpO2 sensor reported high-frequency signal noise.', status: 'alert' },
        { time: '11:20:12 AM', msg: 'Systolic BP critical alarm triggered (160 mmHg).', status: 'alert' },
        { time: '11:25:00 AM', msg: 'Database backup uploaded successfully to hospital server.', status: 'normal' }
    ];

    function populateDeviceLogs() {
        const logBox = document.getElementById('deviceActivityTimeline');
        if (!logBox) return;
        
        logBox.innerHTML = '';
        logsData.forEach(log => {
            const div = document.createElement('div');
            let typeClass = '';
            if (log.status === 'success') typeClass = 'success-log';
            if (log.status === 'alert') typeClass = 'alert-log';
            
            div.className = `activity-log ${typeClass}`;
            div.innerHTML = `
                <span class="activity-log-time">${log.time}</span>
                <span>${log.msg}</span>
            `;
            logBox.appendChild(div);
        });
    }

    // Helper function to dynamically add logs to the Device Activity Timeline
    function addActivityLog(msg, status = 'normal') {
        const now = new Date();
        const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        logsData.unshift({ time: timeStr, msg: msg, status: status });
        if (logsData.length > 30) logsData.pop();
        populateDeviceLogs();
    }

    // Helper function to update the Sepsis Risk Score UI elements on Dashboard & Records tabs
    function updateRiskUI(riskPct, label) {
        // Update dashboard risk badge
        const riskBadge = document.getElementById('riskValueBadge');
        if (riskBadge) {
            riskBadge.innerText = `${riskPct} %`;
            // Alter dashboard risk badge background color based on status
            if (riskPct > 70) {
                riskBadge.style.background = 'var(--color-bp)';
                riskBadge.style.boxShadow = '0 0 10px rgba(255, 23, 68, 0.4)';
            } else if (riskPct > 40) {
                riskBadge.style.background = 'var(--color-hr)';
                riskBadge.style.boxShadow = '0 0 10px rgba(255, 214, 0, 0.4)';
            } else {
                riskBadge.style.background = 'var(--color-spo2)';
                riskBadge.style.boxShadow = '0 0 10px rgba(0, 230, 118, 0.4)';
            }
        }
        
        // Update Records tab Gauge overlay
        const recordsPercent = document.getElementById('recordsRiskPercent');
        const recordsLabel = document.getElementById('recordsRiskLabel');
        const recordsCircle = document.getElementById('recordsRiskCircle');
        
        if (recordsPercent) {
            recordsPercent.innerText = `${riskPct}%`;
        }
        if (recordsLabel) {
            recordsLabel.innerText = label;
        }
        if (recordsCircle) {
            const r = 40;
            const c = Math.PI * 2 * r; // 251.2
            const offset = c - (riskPct / 100) * c;
            recordsCircle.style.strokeDashoffset = offset;
            
            // Toggle colors
            recordsCircle.style.stroke = riskPct > 70 ? 'var(--color-bp)' : (riskPct > 40 ? 'var(--color-hr)' : 'var(--color-spo2)');
        }
    }

    // Function to fetch status from FastAPI backend and update settings/status elements
    function updateSystemStatus() {
        fetch('/api/status')
            .then(res => res.json())
            .then(data => {
                const statusSystem = document.getElementById('statusSystem');
                const statusDatabase = document.getElementById('statusDatabase');
                const statusBackup = document.getElementById('statusBackup');
                const statusUptime = document.getElementById('statusUptime');
                
                if (statusSystem) {
                    statusSystem.innerText = data.status.charAt(0).toUpperCase() + data.status.slice(1);
                    statusSystem.className = `setting-val-tag ${data.status === 'online' ? 'success-text' : 'error-text'}`;
                }
                if (statusDatabase) {
                    statusDatabase.innerText = data.database.charAt(0).toUpperCase() + data.database.slice(1);
                    statusDatabase.className = `setting-val-tag ${data.database === 'connected' ? 'success-text' : 'error-text'}`;
                }
                if (statusBackup) {
                    statusBackup.innerText = data.backup.charAt(0).toUpperCase() + data.backup.slice(1);
                    statusBackup.className = `setting-val-tag ${data.backup === 'up-to-date' ? 'success-text' : 'error-text'}`;
                }
                if (statusUptime) {
                    statusUptime.innerText = data.uptime;
                }
                
                // Update live header indicator
                const liveIndicator = document.getElementById('liveIndicator');
                const liveText = document.getElementById('liveText');
                if (liveIndicator && liveText) {
                    if (data.status === 'online') {
                        liveIndicator.classList.remove('offline');
                        liveText.innerText = 'LIVE';
                    } else {
                        liveIndicator.classList.add('offline');
                        liveText.innerText = 'OFFLINE';
                    }
                }
            })
            .catch(err => {
                console.error("Error updating system status:", err);
            });
    }

    // Event listeners for quick actions
    document.getElementById('btnRestartDevice')?.addEventListener('click', () => {
        const confirmReboot = confirm("Are you sure you want to reboot the connected Edge gateway device remotely?");
        if (confirmReboot) {
            fetch('/api/restart', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    alert(data.message);
                    updateSystemStatus();
                    addActivityLog(data.message, 'success');
                    // Connect websocket if not alive
                    if (!ws || ws.readyState !== WebSocket.OPEN) {
                        connectToAPI();
                    }
                })
                .catch(err => {
                    console.error("Error sending reboot:", err);
                    alert("Failed to send reboot instruction.");
                });
        }
    });

    document.getElementById('btnSyncData')?.addEventListener('click', () => {
        fetch('/api/sync', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                alert(data.message);
                addActivityLog(data.message, 'success');
            })
            .catch(err => {
                console.error("Error syncing data:", err);
                alert("Failed to synchronize database.");
            });
    });

    document.getElementById('btnDisconnectDevice')?.addEventListener('click', () => {
        const confirmDisconnect = confirm("WARNING: Safely disconnect all telemetry stream devices? This will halt real-time logging.");
        if (confirmDisconnect) {
            fetch('/api/disconnect', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    alert(data.message);
                    updateSystemStatus();
                    addActivityLog(data.message, 'alert');
                })
                .catch(err => {
                    console.error("Error disconnecting device:", err);
                    alert("Failed to disconnect devices.");
                });
        }
    });

    // Event listener for generate risk button
    document.getElementById('btnGenerateRisk')?.addEventListener('click', () => {
        fetch('/api/risk', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                hr: currentVitals.hr,
                bp: currentVitals.bp,
                temp: currentVitals.temp,
                spo2: currentVitals.spo2,
                glucose: currentVitals.glucose
            })
        })
        .then(res => res.json())
        .then(data => {
            updateRiskUI(data.risk_percentage, data.status_label);
            addActivityLog(`Generated Sepsis Risk score: ${data.risk_percentage}% (${data.status_label})`, 'normal');
        })
        .catch(err => {
            console.error("Error generating risk:", err);
            alert("Failed to generate clinical risk calculation.");
        });
    });

    // 9. API INTEGRATIONS
    function connectToAPI() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host || 'localhost:8000';
        const wsUrl = `${protocol}//${host}/ws/telemetry`;
        
        ws = new WebSocket(wsUrl);
        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                
                // Handle telemetry offline state message
                if (data.status === 'disconnected') {
                    const liveIndicator = document.getElementById('liveIndicator');
                    const liveText = document.getElementById('liveText');
                    if (liveIndicator && liveText) {
                        liveIndicator.classList.add('offline');
                        liveText.innerText = 'OFFLINE';
                    }
                    return;
                }
                
                // Telemetry is active, ensure indicator is LIVE
                const liveIndicator = document.getElementById('liveIndicator');
                const liveText = document.getElementById('liveText');
                if (liveIndicator && liveText) {
                    liveIndicator.classList.remove('offline');
                    liveText.innerText = 'LIVE';
                }
                
                if (data.hr) currentVitals.hr = data.hr;
                if (data.bp) currentVitals.bp = data.bp;
                if (data.temp) currentVitals.temp = data.temp;
                if (data.spo2) currentVitals.spo2 = data.spo2;
                if (data.glucose) currentVitals.glucose = data.glucose;
                
                updateNumericVitalsUI();
            } catch(e) {
                console.error("Error parsing telemetry WebSocket data", e);
            }
        };
        ws.onclose = () => {
            setTimeout(connectToAPI, 10000);
        };
    }

    function updateNumericVitalsUI() {
        document.getElementById('valBP').innerText = currentVitals.bp;
        document.getElementById('valHR').innerText = currentVitals.hr;
        document.getElementById('valTemp').innerText = currentVitals.temp;
        document.getElementById('valSpO2').innerText = currentVitals.spo2;
        
        if (document.getElementById('vitalsValHR')) {
            document.getElementById('vitalsValHR').innerText = currentVitals.hr;
            document.getElementById('vitalsValSpO2').innerText = currentVitals.spo2;
            document.getElementById('vitalsValBP').innerHTML = `${currentVitals.bp.split('/')[0]} <span class="slash">/</span> ${currentVitals.bp.split('/')[1]}`;
            document.getElementById('vitalsValGlucose').innerText = currentVitals.glucose;
        }
    }

    // Fallback simulation
    setInterval(() => {
        if (!ws || ws.readyState !== WebSocket.OPEN) {
            currentVitals.hr = Math.floor(currentVitals.hr + (Math.random() - 0.5) * 4);
            currentVitals.hr = Math.min(130, Math.max(65, currentVitals.hr));
            currentVitals.spo2 = Math.min(100, Math.max(90, currentVitals.spo2 + (Math.random() - 0.5) * 0.4));
            currentVitals.spo2 = parseFloat(currentVitals.spo2.toFixed(1));
            updateNumericVitalsUI();
        }
    }, 2000);

    // Initial setup calls
    populateTimeline();
    populateMedications();
    populateReports();
    populateDeviceLogs();
    setTheme('dark');
    updateSystemStatus();
    setInterval(updateSystemStatus, 5000);
    
    // Waveforms animation loops
    function loop(time) {
        scrollWaveforms();
        requestAnimationFrame(loop);
    }
    requestAnimationFrame(loop);
    
    // 10. DYNAMIC CHART LEGEND TREND FILTERING
    const legendHR = document.querySelector('.chart-legend .legend-item.hr');
    const legendBP = document.querySelector('.chart-legend .legend-item.bp');
    const legendSpO2 = document.querySelector('.chart-legend .legend-item.spo2');

    legendHR?.addEventListener('click', () => {
        activeTrends.hr = !activeTrends.hr;
        legendHR.classList.toggle('disabled', !activeTrends.hr);
        drawDashboardTelemetry();
    });
    legendBP?.addEventListener('click', () => {
        activeTrends.bp = !activeTrends.bp;
        legendBP.classList.toggle('disabled', !activeTrends.bp);
        drawDashboardTelemetry();
    });
    legendSpO2?.addEventListener('click', () => {
        activeTrends.spo2 = !activeTrends.spo2;
        legendSpO2.classList.toggle('disabled', !activeTrends.spo2);
        drawDashboardTelemetry();
    });

    // 11. DATA MANAGEMENT CONFIGURATION CYCLING
    const autoArchiveRow = document.getElementById('fieldAutoArchive');
    const exportFormatRow = document.getElementById('fieldExportFormat');
    const encryptionRow = document.getElementById('fieldEncryption');

    const autoArchiveOptions = ["30 days", "60 days", "90 days", "180 days", "365 days"];
    const exportFormatOptions = ["HL7 FHIR", "JSON", "CSV", "XML"];
    const encryptionOptions = ["AES-256", "ChaCha20", "DES-56"];

    autoArchiveRow?.addEventListener('click', () => {
        const valSpan = document.getElementById('valAutoArchive');
        if (valSpan) {
            let idx = autoArchiveOptions.indexOf(valSpan.innerText.trim());
            idx = (idx + 1) % autoArchiveOptions.length;
            valSpan.innerText = autoArchiveOptions[idx];
            addActivityLog(`Database Auto-archive threshold updated: ${autoArchiveOptions[idx]}`, 'normal');
        }
    });

    exportFormatRow?.addEventListener('click', () => {
        const valSpan = document.getElementById('valExportFormat');
        if (valSpan) {
            let idx = exportFormatOptions.indexOf(valSpan.innerText.trim());
            idx = (idx + 1) % exportFormatOptions.length;
            valSpan.innerText = exportFormatOptions[idx];
            addActivityLog(`Database Export Format changed: ${exportFormatOptions[idx]}`, 'normal');
        }
    });

    encryptionRow?.addEventListener('click', () => {
        const valSpan = document.getElementById('valEncryption');
        if (valSpan) {
            let idx = encryptionOptions.indexOf(valSpan.innerText.trim());
            idx = (idx + 1) % encryptionOptions.length;
            valSpan.innerText = encryptionOptions[idx];
            addActivityLog(`Database Encryption scheme cycled: ${encryptionOptions[idx]}`, 'normal');
        }
    });

    // 12. GENOGRAM SELECTION & TRAIT MATCH HIGHLIGHTING
    document.querySelectorAll('.tree-node').forEach(node => {
        node.addEventListener('click', () => {
            // Unhighlight previous genogram nodes
            document.querySelectorAll('.tree-node').forEach(n => n.classList.remove('selected-member'));
            node.classList.add('selected-member');
            
            // Reset genetic profile highlights
            document.querySelectorAll('.genetic-row').forEach(row => {
                row.style.outline = 'none';
                row.style.boxShadow = 'none';
                row.style.background = 'transparent';
                row.style.borderRadius = '0';
            });
            
            const relationSpan = node.querySelector('.node-relation');
            const metaSpan = node.querySelector('.node-meta');
            
            if (!relationSpan) return;
            const relation = relationSpan.innerText.toLowerCase();
            const meta = metaSpan ? metaSpan.innerText.toLowerCase() : '';
            
            if (relation.includes('grandfather') || meta.includes('cardio')) {
                const row = document.querySelector('.genetic-row:nth-child(1)'); // Cardio
                if (row) {
                    row.style.outline = '1px solid var(--color-bp)';
                    row.style.boxShadow = '0 0 10px rgba(255, 23, 68, 0.3)';
                    row.style.background = 'rgba(255, 23, 68, 0.05)';
                    row.style.borderRadius = '8px';
                }
            } else if (relation.includes('grandmother') || relation.includes('mother') || relation.includes('sister') || meta.includes('diabetes')) {
                const row = document.querySelector('.genetic-row:nth-child(2)'); // Diabetes
                if (row) {
                    row.style.outline = '1px solid var(--color-bp)';
                    row.style.boxShadow = '0 0 10px rgba(255, 23, 68, 0.3)';
                    row.style.background = 'rgba(255, 23, 68, 0.05)';
                    row.style.borderRadius = '8px';
                }
            } else if (relation.includes('father') || meta.includes('hypertension')) {
                const row = document.querySelector('.genetic-row:nth-child(1)'); // Cardio/Hypertension
                if (row) {
                    row.style.outline = '1px solid var(--color-bp)';
                    row.style.boxShadow = '0 0 10px rgba(255, 23, 68, 0.3)';
                    row.style.background = 'rgba(255, 23, 68, 0.05)';
                    row.style.borderRadius = '8px';
                }
            } else if (relation.includes('uncle') || meta.includes('stroke')) {
                const row = document.querySelector('.genetic-row:nth-child(3)'); // Stroke
                if (row) {
                    row.style.outline = '1px solid var(--color-hr)';
                    row.style.boxShadow = '0 0 10px rgba(255, 214, 0, 0.3)';
                    row.style.background = 'rgba(255, 214, 0, 0.05)';
                    row.style.borderRadius = '8px';
                }
            }
        });
    });

    // 13. SESSION LOCK SCREEN & INACTIVITY ENGINE (PIN 1234)
    const lockScreenModal = document.getElementById('lockScreenModal');
    const lockPinInput = document.getElementById('lockPinInput');
    const lockErrorMsg = document.getElementById('lockErrorMsg');
    const btnUnlockSystem = document.getElementById('btnUnlockSystem');

    function lockSystem() {
        if (isLocked) return;
        isLocked = true;
        
        // Auto navigate to Live Vitals panel
        navItems.forEach(nav => nav.classList.remove('active'));
        const vitalsNav = Array.from(navItems).find(nav => nav.getAttribute('data-page') === 'vitals');
        if (vitalsNav) vitalsNav.classList.add('active');
        
        pagePanels.forEach(panel => {
            panel.classList.remove('active');
            if (panel.id === 'page-vitals') {
                panel.classList.add('active');
            }
        });
        window.dispatchEvent(new Event('resize'));
        
        // Show lock overlay modal
        if (lockScreenModal) {
            lockScreenModal.classList.add('active');
        }
        if (lockPinInput) {
            lockPinInput.value = '';
            lockPinInput.focus();
        }
        if (lockErrorMsg) {
            lockErrorMsg.innerText = '';
        }
        
        addActivityLog("Terminal locked due to user request or inactivity timeout.", "alert");
    }

    function unlockSystem() {
        if (!lockPinInput) return;
        const pin = lockPinInput.value;
        if (pin === '1234') {
            isLocked = false;
            if (lockScreenModal) {
                lockScreenModal.classList.remove('active');
            }
            addActivityLog("Terminal successfully unlocked.", "success");
            resetIdleTimer();
        } else {
            if (lockErrorMsg) {
                lockErrorMsg.innerText = "Invalid PIN. Access Denied.";
            }
            lockPinInput.value = '';
            lockPinInput.focus();
        }
    }

    function resetIdleTimer() {
        lastActiveTime = Date.now();
    }

    // Bind unlock click and key listeners
    btnUnlockSystem?.addEventListener('click', unlockSystem);
    lockPinInput?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') unlockSystem();
    });

    // Bind footer logout button click
    const logoutBtn = document.getElementById('logoutBtn');
    logoutBtn?.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        lockSystem();
    });
    
    // Bind settings logout button click
    const btnSettingsLogout = document.getElementById('btnSettingsLogout');
    btnSettingsLogout?.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        lockSystem();
    });

    // Listen to user interactions to reset idle timer
    ['mousemove', 'keydown', 'click', 'touchstart'].forEach(evtName => {
        window.addEventListener(evtName, () => {
            if (!isLocked) {
                resetIdleTimer();
            }
        });
    });

    // Check inactivity timeout (180 seconds) every 2 seconds
    setInterval(() => {
        if (!isLocked && (Date.now() - lastActiveTime > 180000)) {
            lockSystem();
        }
    }, 2000);

    connectToAPI();

});
