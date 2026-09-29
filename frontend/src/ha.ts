// The slice of Home Assistant's frontend API this card uses, plus small helpers.

export interface HomeAssistant {
  user?: { is_admin: boolean };
  callWS<T>(msg: Record<string, unknown>): Promise<T>;
}

export function fireEvent(node: EventTarget, type: string, detail?: unknown): void {
  node.dispatchEvent(new CustomEvent(type, { detail, bubbles: true, composed: true }));
}

export function toast(node: EventTarget, message: string): void {
  fireEvent(node, "hass-notification", { message });
}

export function errorMessage(err: unknown): string {
  if (err && typeof err === "object" && "message" in err) return String((err as any).message);
  return String(err);
}
