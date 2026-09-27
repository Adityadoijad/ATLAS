/**
 * Turn a chosen image file into a data URL small enough to hold in app state.
 *
 * A phone photo is several megabytes; storing it raw would bloat memory and
 * every render that carries it. Downscaling to a card-sized JPEG keeps the
 * real photo of the real item while staying cheap.
 */
const MAX_EDGE_PX = 1024;
const JPEG_QUALITY = 0.82;

export class UnsupportedImageError extends Error {}

export function readImageAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    if (!file.type.startsWith('image/')) {
      reject(new UnsupportedImageError('Choose an image file.'));
      return;
    }

    const objectUrl = URL.createObjectURL(file);
    const image = new Image();

    image.onload = () => {
      URL.revokeObjectURL(objectUrl);
      const scale = Math.min(1, MAX_EDGE_PX / Math.max(image.width, image.height));
      const canvas = document.createElement('canvas');
      canvas.width = Math.round(image.width * scale);
      canvas.height = Math.round(image.height * scale);

      const context = canvas.getContext('2d');
      if (!context) {
        reject(new UnsupportedImageError('This browser could not process the image.'));
        return;
      }
      context.drawImage(image, 0, 0, canvas.width, canvas.height);
      try {
        resolve(canvas.toDataURL('image/jpeg', JPEG_QUALITY));
      } catch {
        // A cross-origin source would taint the canvas; a picked file never
        // does, but fail cleanly rather than throwing out of the handler.
        reject(new UnsupportedImageError('This image could not be processed.'));
      }
    };

    image.onerror = () => {
      URL.revokeObjectURL(objectUrl);
      reject(new UnsupportedImageError('That file could not be read as an image.'));
    };

    image.src = objectUrl;
  });
}
