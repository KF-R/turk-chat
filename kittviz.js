// Constants
const numBars = 10; // Max
const fadedTips = 3; // Number of lower intensity fade-out bars at the end of a column
const columnPadding = 12; // Horizontal gap between columns
const centerBonus = 2; // How many extra bars to insert into the centre column
const barWidth = 15; 
const barHeight = 5;
const barPadding = 1;  // vertical gap between bars
const kittCanvasWidth = ( (barWidth * 3) + (columnPadding * 4) );
const kittCanvasHeight = (barHeight + barPadding) * (1 + numBars + (fadedTips + centerBonus)) * 2;
const COLOUR = [1, 0, 0]  // Boolean RGB flags, i.e. [1, 0, 1] would be magenta, [0, 1, 1] cyan etc.

// Canvas setup
const kitt_canvas = document.getElementById('kitt');
kitt_canvas.width = kittCanvasWidth;
kitt_canvas.height = kittCanvasHeight;
const kitt_ctx = kitt_canvas.getContext('2d');

function drawKittFrame(n, colour_flags=[1, 0, 0]) {
    // Draws KITT's visualization on the 'kitt' canvas at the
    // level `n`, where `n` is an integer between 0 and 10 inclusive.
    // `colour_flags` has binary boolean flags for RGB.

    kitt_ctx.fillStyle = 'rgb(0,0,0)';
    kitt_ctx.fillRect(0,0,kitt_canvas.width,kitt_canvas.height);
    if (n == 0) return;
    for (let col = 0; col < 3; col++) {
        let colBonus = col == 1 ? centerBonus : 0;
        let intensity = 255;
        for (let i = 0; i < n + colBonus + fadedTips; i++) {
            if (i < n + colBonus) {
                kitt_ctx.fillStyle = `rgb(${intensity * colour_flags[0]}, ${intensity * colour_flags[1]}, ${intensity * colour_flags[2]})`;
            } else {
                intensity = intensity - Math.floor(255 / (fadedTips + 1));
                kitt_ctx.fillStyle = `rgb(${intensity * colour_flags[0]}, ${intensity * colour_flags[1]}, ${intensity * colour_flags[2]})`;
            }
            kitt_ctx.fillRect(columnPadding + (col * (barWidth + columnPadding)), Math.floor(kitt_canvas.height / 2) + (i * (barHeight + barPadding)), barWidth, barHeight);
            kitt_ctx.fillRect(columnPadding + (col * (barWidth + columnPadding)), Math.floor(kitt_canvas.height / 2) - ( (i + 1) * (barHeight + barPadding)), barWidth, barHeight);
        }
    }
}