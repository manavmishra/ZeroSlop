declare module "reliability:pages-editor" {
  export function onRequestPost(context: { request: Request; env: unknown }): Promise<Response>;
}
