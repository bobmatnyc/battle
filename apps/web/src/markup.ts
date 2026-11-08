// HTML/SVG text escaping shared by every markup module.
const ENTITIES: Record<string, string> = {"&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;"};

/** Every server string passes through this before it reaches markup. */
export const esc = (value: unknown): string => String(value ?? "").replace(/[&<>"']/g, (c) => ENTITIES[c] ?? c);
