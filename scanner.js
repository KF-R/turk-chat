// Constants
const numSquares = 21;
const squareWidth = 16; // Adjust size of squares here
const squarePadding = 1;
const canvasWidth = numSquares * (squareWidth + squarePadding);

// Canvas setup
const canvas = document.getElementById('scanner-canvas');
const ctx = canvas.getContext('2d');
canvas.width = canvasWidth;
canvas.height = squareWidth;

// Larson scanner variables
let position = Math.floor(numSquares / 2); // Current position of the light
let direction = 1; // Direction of the light movement

var scanner_speed = 5;
var scanner_mode = 'Cylon'; // Default mode
var scanner_paused = false;
var scanner_colour_flags = [1, 0, 0]; // 0 or 1 to disable/enable RGB component of scanner colour

// Draw the base row of squares
function drawSquares() {
    for (let i = 0; i < numSquares; i++) {
        ctx.fillStyle = 'black';
        ctx.fillRect(i * (squareWidth + squarePadding), 0, squareWidth, squareWidth);
    }
}

// Update the scanner position
function updateScanner() {
    drawSquares(); // Redraw base squares

    if (scanner_paused) return;


    let sideLights; // Determine how far the side lights extend based on the mode
    if (scanner_mode === 'Cylon') {
        sideLights = 1;
    } else if (scanner_mode === 'Kitt') {
        sideLights = 4;
    }

    // Depending on the mode, draw the light pattern
    for (let i = -sideLights; i <= sideLights; i++) {
        let intensity;
        if (scanner_mode === 'Cylon') {
            intensity = 255 - Math.abs(i) * 100; // Decrease intensity for side squares in Cylon mode
        } else if (scanner_mode === 'Kitt') {
            intensity = 255 - Math.abs(i) * 50; // Decrease intensity progressively in Kitt mode
        }
        ctx.fillStyle = `rgb(${intensity * scanner_colour_flags[0]}, ${intensity * scanner_colour_flags[1]}, ${intensity * scanner_colour_flags[2]})`;
        let pos = position + i;
        if (pos >= -sideLights && pos < numSquares + sideLights) { // Draw only if within extended range
            ctx.fillRect(Math.max(0, pos) * (squareWidth + squarePadding), 0, squareWidth, squareWidth);
        }
    }

    // Move the main light
    position += direction;

    // Change direction at the extended ends, considering the side lights
    ctx.fillStyle = `rgb(${255 * scanner_colour_flags[0]}, ${255 * scanner_colour_flags[1]}, ${255 * scanner_colour_flags[2]})`;
    if (position < 1) {
        ctx.fillRect(0, 0, squareWidth, squareWidth);
    }
    if ( (position > numSquares - 1) || (position == numSquares - 1 && direction < 1) ){
        ctx.fillRect((numSquares - 1 ) * (squareWidth + squarePadding), 0, squareWidth, squareWidth);
    }
    if (position === -sideLights || position === numSquares - 1 + sideLights) {
        direction *= -1; // Change direction
    }
}

// Animation loop
function animate() {
    setTimeout(() => {
        requestAnimationFrame(animate);
        updateScanner();
    }, scanner_speed);
}

// Change scanner mode
function changeMode(newMode = '') {
    position = Math.floor(numSquares / 2); // Prevents modes with less sidelights getting stuck at direction change
    if (newMode == '') {
        scanner_mode = scanner_mode === 'Cylon' ? 'Kitt' : 'Cylon';
    } else if (newMode == 'Cylon') {
        scanner_mode = 'Cylon';
    } else {
        scanner_mode = 'Kitt';
    }
}

// Initialize
drawSquares();
animate();
