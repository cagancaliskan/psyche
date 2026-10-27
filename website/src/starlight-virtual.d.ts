// Starlight's virtual modules that components/chrome/Search.astro imports, as Starlight's own source
// declares them; the package ships no declarations for them. Only what the component reads is typed.

declare module 'virtual:starlight/project-context' {
  const project: { trailingSlash: 'always' | 'never' | 'ignore' };
  export default project;
}

declare module 'virtual:starlight/pagefind-config' {
  export const pagefindUserConfig: Record<string, unknown>;
}
