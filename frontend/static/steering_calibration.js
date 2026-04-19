const API_BASE = '';
const TEST_TURN_ANGLE = 25;

let currentOffset = 0;

function setConnectionStatus(connected) {
    const statusEl = document.getElementById('status');
    if (connected) {
        statusEl.textContent = '● Connected';
        statusEl.classList.remove('disconnected');
        statusEl.classList.add('connected');
    } else {
        statusEl.textContent = '● Disconnected';
        statusEl.classList.remove('connected');
        statusEl.classList.add('disconnected');
    }
}

async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE}/api/health`);
        const data = await response.json();
        setConnectionStatus(data.status === 'ok');
    } catch (error) {
        console.error('Health check failed:', error);
        setConnectionStatus(false);
    }
}

async function updateSteeringStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/steering/status`);
        const data = await response.json();
        document.getElementById('steering-now').textContent = `Current Angle: ${data.angle}°`;
    } catch (error) {
        console.error('Failed to fetch steering status:', error);
    }
}

async function loadCalibration() {
    try {
        const response = await fetch(`${API_BASE}/api/steering/calibration`);
        const data = await response.json();
        currentOffset = parseInt(data.offset, 10) || 0;
        const slider = document.getElementById('offset-slider');
        slider.value = currentOffset;
        document.getElementById('offset-value').textContent = currentOffset;
    } catch (error) {
        console.error('Failed to load calibration:', error);
    }
}

function nudgeOffset(delta) {
    const slider = document.getElementById('offset-slider');
    const next = Math.max(-30, Math.min(30, parseInt(slider.value, 10) + delta));
    slider.value = next;
    document.getElementById('offset-value').textContent = next;
}

async function saveCalibration() {
    try {
        const offset = parseInt(document.getElementById('offset-slider').value, 10);
        const response = await fetch(`${API_BASE}/api/steering/calibration`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ offset })
        });

        const data = await response.json();
        currentOffset = data.offset;
        document.getElementById('offset-value').textContent = currentOffset;
        await testCenter();
    } catch (error) {
        console.error('Failed to save calibration:', error);
    }
}

async function resetCalibration() {
    try {
        await fetch(`${API_BASE}/api/steering/calibration/reset`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        await loadCalibration();
        await testCenter();
    } catch (error) {
        console.error('Failed to reset calibration:', error);
    }
}

async function testLeft() {
    try {
        await fetch(`${API_BASE}/api/steering/angle`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ angle: -TEST_TURN_ANGLE })
        });
        await updateSteeringStatus();
    } catch (error) {
        console.error('Failed test left:', error);
    }
}

async function testRight() {
    try {
        await fetch(`${API_BASE}/api/steering/angle`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ angle: TEST_TURN_ANGLE })
        });
        await updateSteeringStatus();
    } catch (error) {
        console.error('Failed test right:', error);
    }
}

async function testCenter() {
    try {
        await fetch(`${API_BASE}/api/steering/center`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        await updateSteeringStatus();
    } catch (error) {
        console.error('Failed test center:', error);
    }
}

document.addEventListener('DOMContentLoaded', async function() {
    const slider = document.getElementById('offset-slider');

    slider.addEventListener('input', function() {
        document.getElementById('offset-value').textContent = this.value;
    });

    document.getElementById('decrease-offset').addEventListener('click', function() {
        nudgeOffset(-1);
    });

    document.getElementById('increase-offset').addEventListener('click', function() {
        nudgeOffset(1);
    });

    document.getElementById('apply-offset').addEventListener('click', saveCalibration);
    document.getElementById('reset-offset').addEventListener('click', resetCalibration);
    document.getElementById('test-left').addEventListener('click', testLeft);
    document.getElementById('test-center').addEventListener('click', testCenter);
    document.getElementById('test-right').addEventListener('click', testRight);

    await checkHealth();
    await loadCalibration();
    await updateSteeringStatus();

    setInterval(checkHealth, 5000);
    setInterval(updateSteeringStatus, 1000);
});
