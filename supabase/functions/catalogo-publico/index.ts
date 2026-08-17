// AlphaFest Manager 20.4.9-I8.9.1
// Renderiza exclusivamente os HTMLs de catálogos publicados no bucket público `catalogo`.
// Supabase Storage serve arquivos HTML como text/plain por segurança; esta função
// devolve o mesmo conteúdo com Content-Type text/html para navegação do cliente.

const RENDER_VERSION = "I8.9.1"
const PATH_OK = /^catalogos-publicos\/[A-Za-z0-9_-]+\/[A-Za-z0-9_.-]+\.html$/

function headers(extra: Record<string, string> = {}) {
  return {
    "X-AlphaFest-Catalog-Renderer": RENDER_VERSION,
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    ...extra,
  }
}

Deno.serve(async (req) => {
  try {
    const requestUrl = new URL(req.url)

    if (requestUrl.searchParams.get("health") === "1") {
      return new Response("AlphaFest catalog renderer online", {
        status: 200,
        headers: headers({
          "Content-Type": "text/plain; charset=utf-8",
          "Cache-Control": "no-store",
        }),
      })
    }

    if (req.method !== "GET" && req.method !== "HEAD") {
      return new Response("Método não permitido", {
        status: 405,
        headers: headers({ "Allow": "GET, HEAD" }),
      })
    }

    const objectPath = (requestUrl.searchParams.get("path") || "").trim().replace(/^\/+/, "")
    if (!PATH_OK.test(objectPath)) {
      return new Response("Caminho de catálogo inválido", {
        status: 400,
        headers: headers({ "Content-Type": "text/plain; charset=utf-8" }),
      })
    }

    const supabaseUrl = (Deno.env.get("SUPABASE_URL") || "").replace(/\/$/, "")
    if (!supabaseUrl) {
      return new Response("SUPABASE_URL indisponível", {
        status: 500,
        headers: headers({ "Content-Type": "text/plain; charset=utf-8" }),
      })
    }

    const encodedPath = objectPath.split("/").map(encodeURIComponent).join("/")
    const storageUrl = `${supabaseUrl}/storage/v1/object/public/catalogo/${encodedPath}`
    const upstream = await fetch(storageUrl, {
      method: "GET",
      redirect: "follow",
      headers: { "Accept": "text/plain,text/html;q=0.9,*/*;q=0.8" },
    })

    if (!upstream.ok) {
      return new Response("Catálogo não encontrado", {
        status: upstream.status === 404 ? 404 : 502,
        headers: headers({ "Content-Type": "text/plain; charset=utf-8" }),
      })
    }

    const body = req.method === "HEAD" ? null : await upstream.arrayBuffer()
    return new Response(body, {
      status: 200,
      headers: headers({
        "Content-Type": "text/html; charset=utf-8",
        "Content-Disposition": "inline",
        "Cache-Control": "public, max-age=300, s-maxage=300",
        "Access-Control-Allow-Origin": "*",
      }),
    })
  } catch (_error) {
    return new Response("Falha ao abrir catálogo", {
      status: 500,
      headers: headers({ "Content-Type": "text/plain; charset=utf-8" }),
    })
  }
})
