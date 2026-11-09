// Password reset UI is hidden until the server can send email. Opt in at
// build time with VITE_PASSWORD_RESET_ENABLED=true. Pages and backend
// endpoints stay in place; only the link and routes are gated.
export function isPasswordResetEnabled(): boolean {
  return import.meta.env.VITE_PASSWORD_RESET_ENABLED === "true";
}
