// PiCar-X Control JavaScript

const API_BASE = '';
let currentSpeed = 50;
let currentPan = 0;
let currentTilt = 0;
let currentSteering = 0;
const STEERING_TURN_ANGLE = 25;
let frameCount = 0;
let lastFpsTime = Date.now();

// ===== Initialization =====
document.addEventListener('DOMContentLoaded', function() {
    console.log('PiCar-X Control Interface loaded');
    checkHealth();
    updateCameraStatus();
    updateSteeringStatus();
    setInterval(checkHealth, 5000);
    setInterval(updateCameraStatus, 1000);
    setInterval(updateSteeringStatus, 1000);
    setupKeyboardControl();
});

// ===== Health Check =====
async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE}/api/health`);
        const data = await response.json();
        
        if (data.status === 'ok') {
            setConnectionStatus(true);
        } else {
            setConnectionStatus(false);
        }
    } catch (error) {
        console.error('Health check failed:', error);
        setConnectionStatus(false);
    }
}

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

// ===== Motor Control =====
async function moveForward() {
    try {
        const speed = parseInt(document.getElementById('speed-slider').value);
        await fetch(`${API_BASE}/api/motors/forward`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ speed: speed })
        });
        updateMotorStatus();
    } catch (error) {
        console.error('Forward command failed:', error);
    }
}

async function moveBackward() {
    try {
        const speed = parseInt(document.getElementById('speed-slider').value);
        await fetch(`${API_BASE}/api/motors/backward`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ speed: speed })
        });
        updateMotorStatus();
    } catch (error) {
        console.error('Backward command failed:', error);
    }
}

async function moveLeft() {
    try {
        await fetch(`${API_BASE}/api/steering/angle`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ angle: -STEERING_TURN_ANGLE })
        });
        updateSteeringStatus();
    } catch (error) {
        console.error('Left command failed:', error);
    }
}

async function moveRight() {
    try {
        await fetch(`${API_BASE}/api/steering/angle`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ angle: STEERING_TURN_ANGLE })
        });
        updateSteeringStatus();
    } catch (error) {
        console.error('Right command failed:', error);
    }
}

async function centerSteering() {
    try {
        await fetch(`${API_BASE}/api/steering/center`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        updateSteeringStatus();
    } catch (error) {
        console.error('Center steering failed:', error);
    }
}

async function stopMotors() {
    try {
        await fetch(`${API_BASE}/api/motors/stop`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        await fetch(`${API_BASE}/api/steering/center`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        updateMotorStatus();
        updateSteeringStatus();
        document.getElementById('left-slider').value = 0;
        document.getElementById('right-slider').value = 0;
        document.getElementById('left-manual').textContent = 0;
        document.getElementById('right-manual').textContent = 0;
    } catch (error) {
        console.error('Stop command failed:', error);
    }
}

async function setIndividualSpeed(leftSpeed, rightSpeed) {
    try {
        await fetch(`${API_BASE}/api/motors/set-speed`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                left_speed: parseInt(leftSpeed),
                right_speed: parseInt(rightSpeed)
            })
        });
        document.getElementById('left-manual').textContent = leftSpeed;
        document.getElementById('right-manual').textContent = rightSpeed;
        updateMotorStatus();
    } catch (error) {
        console.error('Speed control failed:', error);
    }
}

async function updateMotorStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/motors/status`);
        const data = await response.json();
        
        document.getElementById('left-speed').textContent = 
            data.left_speed + '%';
        document.getElementById('right-speed').textContent = 
            data.right_speed + '%';
    } catch (error) {
        console.error('Failed to update motor status:', error);
    }
}

async function updateSteeringStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/steering/status`);
        const data = await response.json();
        currentSteering = data.angle;
        document.getElementById('steering-angle').textContent = `${currentSteering}°`;
    } catch (error) {
        console.error('Failed to update steering status:', error);
    }
}

// ===== Camera Control =====
async function moveCamera(panDelta, tiltDelta) {
    try {
        const newPan = Math.max(-90, Math.min(90, currentPan + panDelta));
        const newTilt = Math.max(-90, Math.min(90, currentTilt + tiltDelta));
        
        await fetch(`${API_BASE}/api/camera/position`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pan: newPan, tilt: newTilt })
        });
        updateCameraStatus();
    } catch (error) {
        console.error('Camera move failed:', error);
    }
}

async function centerCamera() {
    try {
        await fetch(`${API_BASE}/api/camera/center`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        updateCameraStatus();
    } catch (error) {
        console.error('Center camera failed:', error);
    }
}

async function updateCameraStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/camera/status`);
        const data = await response.json();
        
        currentPan = data.pan;
        currentTilt = data.tilt;
        
        document.getElementById('pan-value').textContent = currentPan;
        document.getElementById('tilt-value').textContent = currentTilt;
    } catch (error) {
        console.error('Failed to update camera status:', error);
    }
}

// ===== Speed Control =====
function updateSpeedDisplay(value) {
    document.getElementById('speed-value').textContent = value;
    currentSpeed = parseInt(value);
}

// ===== Stream Monitoring =====
document.addEventListener('DOMContentLoaded', function() {
    const streamImg = document.getElementById('stream');
    streamImg.addEventListener('load', function() {
        frameCount++;
        const now = Date.now();
        const elapsed = (now - lastFpsTime) / 1000;
        
        if (elapsed >= 1) {
            const fps = Math.round(frameCount / elapsed);
            document.getElementById('fps').textContent = `FPS: ${fps}`;
            frameCount = 0;
            lastFpsTime = now;
        }
    });
});

// ===== Keyboard Control =====
function setupKeyboardControl() {
    const keys = {};
    
    document.addEventListener('keydown', function(e) {
        keys[e.key.toLowerCase()] = true;
        
        // Arrow keys or WASD
        if (e.key === 'ArrowUp' || e.key.toLowerCase() === 'w') {
            moveForward();
            e.preventDefault();
        } else if (e.key === 'ArrowDown' || e.key.toLowerCase() === 's') {
            moveBackward();
            e.preventDefault();
        } else if (e.key === 'ArrowLeft' || e.key.toLowerCase() === 'a') {
            moveLeft();
            e.preventDefault();
        } else if (e.key === 'ArrowRight' || e.key.toLowerCase() === 'd') {
            moveRight();
            e.preventDefault();
        } else if (e.key === ' ') {
            stopMotors();
            e.preventDefault();
        }
        
        // Camera controls with numeric keypad
        if (e.key === '4') moveCamera(-10, 0);  // Pan left
        if (e.key === '6') moveCamera(10, 0);   // Pan right
        if (e.key === '8') moveCamera(0, -10);  // Tilt up
        if (e.key === '2') moveCamera(0, 10);   // Tilt down
        if (e.key === '5') centerCamera();      // Center camera
    });
    
    document.addEventListener('keyup', function(e) {
        if (e.key === 'ArrowUp' || e.key === 'ArrowDown' ||
            e.key.toLowerCase() === 'w' || e.key.toLowerCase() === 's') {
            stopMotors();
        }

        if (e.key === 'ArrowLeft' || e.key === 'ArrowRight' ||
            e.key.toLowerCase() === 'a' || e.key.toLowerCase() === 'd') {
            centerSteering();
        }
    });
}
