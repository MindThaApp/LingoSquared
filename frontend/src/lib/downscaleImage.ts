// Client-side downscale for feedback-widget photo attachments -- see
// docs/CONTRACT.md "Feedback attachments": "client-side downscale to
// ≤1600px longest edge before upload to keep mobile uploads fast." A
// phone camera photo can be 4000px+ and several MB; shrinking before the
// network request (not just relying on the server's 5MB cap) keeps
// mobile uploads fast and avoids failing the cap unnecessarily.
//
// Falls back to the original file untouched if canvas/createImageBitmap
// isn't available or decoding fails -- the server-side content-type sniff
// and size cap are the real enforcement; this is a best-effort optimization.
const MAX_EDGE = 1600;
const OUTPUT_TYPE = "image/jpeg";
const OUTPUT_QUALITY = 0.85;

export async function downscaleImage(file: File): Promise<File> {
  try {
    const bitmap = await createImageBitmap(file);
    const { width, height } = bitmap;
    const longestEdge = Math.max(width, height);
    if (longestEdge <= MAX_EDGE) {
      bitmap.close?.();
      return file;
    }

    const scale = MAX_EDGE / longestEdge;
    const targetWidth = Math.round(width * scale);
    const targetHeight = Math.round(height * scale);

    const canvas = document.createElement("canvas");
    canvas.width = targetWidth;
    canvas.height = targetHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      bitmap.close?.();
      return file;
    }
    ctx.drawImage(bitmap, 0, 0, targetWidth, targetHeight);
    bitmap.close?.();

    const blob: Blob | null = await new Promise((resolve) =>
      canvas.toBlob(resolve, OUTPUT_TYPE, OUTPUT_QUALITY),
    );
    if (!blob) return file;

    const newName = file.name.replace(/\.\w+$/, "") + ".jpg";
    return new File([blob], newName, { type: OUTPUT_TYPE });
  } catch {
    return file;
  }
}
