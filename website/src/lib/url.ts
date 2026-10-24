/** Join a site-relative path onto the configured base ('/psyche/'), with exactly one slash. */
export function withBase(path: string): string {
  const base = import.meta.env.BASE_URL.endsWith('/') ? import.meta.env.BASE_URL : `${import.meta.env.BASE_URL}/`;
  return base + path.replace(/^\/+/, '');
}
