#!/usr/bin/env node
/*
 * Regenerates the PWA / Microsoft Store icon set in frontend/public/icons/.
 *
 *   node frontend/scripts/generate-pwa-icons.mjs
 *
 * Source: frontend/public/favicon.svg (the brand bolt). The old
 * icons/icon-512.png was NOT used as the source: it was a 512x512 white
 * square with the bolt rasterised at ~82x78 px in its top-left corner, so
 * upscaling it would have been blurry and badly framed.
 *
 * Outputs (all PNG, written only inside frontend/public/icons/):
 *   icon-<n>.png           purpose "any": bolt centred on a transparent
 *                          square, ~10% margin each side.
 *   icon-maskable-<n>.png  purpose "maskable": full-bleed brand background,
 *                          bolt kept inside the central 80% safe zone
 *                          (W3C maskable spec: a circle of radius 40%).
 *   shortcut-*.png         96px shortcut icons for the manifest.
 *
 * Uses sharp (already installed via @huggingface/transformers). Output is
 * deterministic for a given sharp/libvips version, so re-running it only
 * changes files when the source or this script changes.
 */
import { mkdirSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import sharp from "sharp";

const here = dirname(fileURLToPath(import.meta.url));
const publicDir = resolve(here, "../public");
const outDir = resolve(publicDir, "icons");
const svg = readFileSync(resolve(publicDir, "favicon.svg"));

// Store tile/logo sizes (44, 50, 71, 150, 310), the classic PWA sizes
// (192, 512) and a 1024 master for the Store listing / PWABuilder.
const ANY_SIZES = [44, 50, 71, 150, 192, 310, 512, 1024];
const MASKABLE_SIZES = [192, 512];
const MASKABLE_BG = "#4a3bff"; // theme_color / --accent
const MASKABLE_FG_BG = "#ffffff"; // white disc behind the bolt so it reads on the accent

mkdirSync(outDir, { recursive: true });

/** The bolt rendered to fit inside a `box` x `box` square, transparent. */
async function bolt(box) {
  // Render the SVG at a high density, then fit it into the box.
  return sharp(svg, { density: 1200 })
    .resize(box, box, { fit: "contain", background: { r: 0, g: 0, b: 0, alpha: 0 } })
    .png()
    .toBuffer();
}

async function anyIcon(size) {
  const box = Math.round(size * 0.8);
  const off = Math.round((size - box) / 2);
  await sharp({ create: { width: size, height: size, channels: 4, background: { r: 0, g: 0, b: 0, alpha: 0 } } })
    .composite([{ input: await bolt(box), left: off, top: off }])
    .png({ compressionLevel: 9 })
    .toFile(resolve(outDir, `icon-${size}.png`));
}

async function maskableIcon(size) {
  // Safe zone = circle of diameter 0.8*size. A white disc of diameter
  // 0.72*size sits inside it, and the bolt fits a 0.46*size square whose
  // corners stay inside the disc (0.46*sqrt2 = 0.65 < 0.72).
  const disc = Math.round(size * 0.72);
  const discSvg = Buffer.from(
    `<svg xmlns="http://www.w3.org/2000/svg" width="${disc}" height="${disc}"><circle cx="${disc / 2}" cy="${disc / 2}" r="${disc / 2}" fill="${MASKABLE_FG_BG}"/></svg>`,
  );
  const box = Math.round(size * 0.46);
  await sharp({ create: { width: size, height: size, channels: 4, background: MASKABLE_BG } })
    .composite([
      { input: discSvg, left: Math.round((size - disc) / 2), top: Math.round((size - disc) / 2) },
      { input: await bolt(box), left: Math.round((size - box) / 2), top: Math.round((size - box) / 2) },
    ])
    .png({ compressionLevel: 9 })
    .toFile(resolve(outDir, `icon-maskable-${size}.png`));
}

async function shortcutIcon(name, glyphSvg) {
  const size = 96;
  const bg = Buffer.from(
    `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 96 96">` +
      `<rect width="96" height="96" rx="22" fill="${MASKABLE_BG}"/>${glyphSvg}</svg>`,
  );
  await sharp(bg, { density: 300 }).resize(size, size).png({ compressionLevel: 9 }).toFile(resolve(outDir, `shortcut-${name}.png`));
}

for (const s of ANY_SIZES) await anyIcon(s);
for (const s of MASKABLE_SIZES) await maskableIcon(s);
// Continue learning: a "play" triangle. Practice: a circular-arrows "repeat".
await shortcutIcon("continue", '<path d="M38 28 L70 48 L38 68 Z" fill="#ffffff"/>');
await shortcutIcon(
  "practice",
  '<g fill="none" stroke="#ffffff" stroke-width="7" stroke-linecap="round" stroke-linejoin="round">' +
    '<path d="M28 44a20 20 0 0 1 34-12l6 6"/><path d="M68 26v12H56"/>' +
    '<path d="M68 52a20 20 0 0 1-34 12l-6-6"/><path d="M28 70V58h12"/></g>',
);
console.log(`wrote icons to ${outDir}`);
