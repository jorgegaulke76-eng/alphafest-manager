// AlphaFest: avisos de atividade a partir das métricas já coletadas.
// Este Worker NÃO recebe requisições do público nem altera o site.
const WINDOW_MS = 5 * 60 * 1000;
const MAX_ROWS = 1000;
const EVENT_TYPES = new Set(["page_view", "product_open", "whatsapp_click"]);

export function windowFor(scheduledTime) {
  const ms = Number(scheduledTime);
  if (!Number.isFinite(ms) || ms <= 0) throw new TypeError("Invalid scheduled time");
  const endMs = Math.floor(ms / WINDOW_MS) * WINDOW_MS;
  return {
    start: new Date(endMs - WINDOW_MS),
    end: new Date(endMs)
  };
}

export function isTechnicalPath(input) {
  let path = String(input || "/").split("?")[0].split("#")[0].trim().toLowerCase();
  if (!path.startsWith("/")) path = "/" + path;
  const segments = path.split("/").filter(Boolean);
  const basename = segments.at(-1) || "";
  return (
    segments.includes(".well-known") ||
    segments.includes("wp-admin") ||
    segments.includes("wp-json") ||
    /^\/(api|cdn-cgi)\//.test(path) ||
    /^(robots\.txt|ads\.txt|favicon\.ico|sitemap\.xml|manifest\.webmanifest|sw\.js|offline\.html|404\.html)$/i.test(basename)
  );
}

export function summarizeRows(rows) {
  if (!Array.isArray(rows)) throw new TypeError("Expected list");
  const sessions = new Set();
  let pageViews = 0, opened = 0, whatsapp = 0;
  for (const row of rows) {
    if (!row || !EVENT_TYPES.has(row.event_type)) continue;
    if (isTechnicalPath(row.page_path)) continue;
    if (row.event_type === "page_view") {
      pageViews++;
      const session = String(row.session_id || "").trim();
      if (session) sessions.add(session);
    } else if (row.event_type === "product_open") opened++;
    else if (row.event_type === "whatsapp_click") whatsapp++;
  }
  return { pageViews, sessions: sessions.size, opened, whatsapp, truncated: rows.length >= MAX_ROWS };
}

function horaEmBrasilia(utcDate) {
  return new Intl.DateTimeFormat("pt-BR", {
    timeZone: "America/Sao_Paulo", hour: "2-digit", minute: "2-digit", hour12: false
  }).format(utcDate);
}

// O destaque reflete eventos registrados, não novos pedidos nem mensagens recebidas.
export function classifyAlert(summary) {
  if (summary.whatsapp > 0) return "whatsapp";
  if (summary.opened > 0) return "products";
  return "visits";
}

export function formatAlert(summary, period) {
  const type = classifyAlert(summary);
  const headline = type === "whatsapp"
    ? "🚨 AlphaFest — clique no WhatsApp detectado"
    : type === "products"
      ? "🎁 AlphaFest — interesse em produtos no site"
      : "🔔 AlphaFest — atividade no site";
  const lines = [
    headline
    "🕒 " + horaEmBrasilia(period.start) + "–" + horaEmBrasilia(period.end) + " (Brasília)",
    "🌐 Acessos registrados: " + summary.pageViews,
    "📱 Sessões estimadas: " + summary.sessions,
    "🎁 Produtos consultados: " + summary.opened,
    "💬 Cliques para o WhatsApp: " + summary.whatsapp
  ];
  if (type === "whatsapp") {
    lines.push("", "📌 Ação sugerida: conferir as conversas no WhatsApp Business.");
    lines.push("⚠️ Clique não confirma mensagem enviada, orçamento ou venda.");
  } else if (type === "products") {
    lines.push("", "👀 Produtos consultados; acompanhe eventuais contatos.");
  }
  if (summary.truncated) lines.push("⚠️ Movimento alto: contagem parcial.");
  lines.push("", "São eventos do site, não identificação de pessoas ou vendas.");
  return lines.join("\n");
}

export function supabaseRequest(env, period) {
  const base = String(env.SUPABASE_URL || "").replace(/\/+$/, "");
  const key = String(env.SUPABASE_SECRET_KEY || "");
  if (!base.startsWith("https://") || !key) throw new Error("Supabase secrets are missing");
  const url = new URL(base + "/rest/v1/site_metrics_events");
  url.searchParams.set("select", "event_type,session_id,page_path");
  url.searchParams.set("event_type", "in.(page_view,product_open,whatsapp_click)");
  url.searchParams.append("created_at", "gte." + period.start.toISOString());
  url.searchParams.append("created_at", "lt." + period.end.toISOString());
  url.searchParams.set("order", "created_at.asc");
  url.searchParams.set("limit", String(MAX_ROWS));
  const headers = { apikey: key, Accept: "application/json" };
  // Novas chaves sb_secret_* não são JWT.
  if (!key.startsWith("sb_secret_")) headers.Authorization = "Bearer " + key;
  return { url: url.toString(), init: { method: "GET", headers } };
}

export async function executeAlert(scheduledTime, env, fetcher = fetch) {
  if (String(env.ALERTS_ENABLED || "false").toLowerCase() !== "true") {
    return { status: "disabled" };
  }
  const token = String(env.TELEGRAM_BOT_TOKEN || "");
  const chatId = String(env.TELEGRAM_CHAT_ID || "");
  if (!token || !/^-?\d+$/.test(chatId)) {
    throw new Error("Telegram secrets are missing");
  }
  const period = windowFor(scheduledTime);
  const request = supabaseRequest(env, period);
  const source = await fetcher(request.url, request.init);
  if (!source.ok) throw new Error("Error reading website metrics");
  const rows = await source.json();
  const summary = summarizeRows(rows);
  if (summary.pageViews === 0 && summary.whatsapp === 0) {
    return { status: "no-activity", summary };
  }
  const text = formatAlert(summary, period);
  const sent = await fetcher("https://api.telegram.org/bot" + token + "/sendMessage", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      chat_id: chatId,
      text,
      disable_notification: false,
      link_preview_options: { is_disabled: true }
    })
  });
  if (!sent.ok) throw new Error("Error sending Telegram alert");
  const result = await sent.json();
  if (!result || result.ok !== true) throw new Error("Telegram did not confirm delivery");
  return { status: "sent", summary };
}

export default {
  // Nenhum endpoint público é exposto para disparar notificações.
  async fetch() {
    return new Response("Not found", { status: 404, headers: { "Cache-Control": "no-store" } });
  },
  async scheduled(controller, env) {
    return executeAlert(controller.scheduledTime, env);
  }
};
