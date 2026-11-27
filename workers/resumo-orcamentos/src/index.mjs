// Resumo agregado diario de orcamentos reais, separado do Worker de visitas.
// Nenhum nome, telefone, valor, numero de proposta ou mensagem sai do Worker.
const MAX_RECORDS = 10000;

function truthy(v) {
  return v === true || v === 1 || ["1", "true", "sim", "yes", "ok", "aprovado", "pago", "pronto", "entregue"].includes(String(v ?? "").trim().toLowerCase());
}
function dateOnly(v) {
  if (!v) return null;
  const s = String(v).trim();
  const br = /^(\d{2})\/(\d{2})\/(\d{4})/.exec(s);
  const iso = /^(\d{4})-(\d{2})-(\d{2})/.exec(s);
  const parts = br ? [Number(br[3]), Number(br[2]), Number(br[1])] :
    iso ? [Number(iso[1]), Number(iso[2]), Number(iso[3])] : null;
  if (!parts) return null;
  const [y,m,d] = parts;
  const t = Date.UTC(y,m-1,d);
  const dt = new Date(t);
  return dt.getUTCFullYear()===y && dt.getUTCMonth()+1===m && dt.getUTCDate()===d ? t : null;
}
function brDate(clock) {
  return new Intl.DateTimeFormat("en-CA",{timeZone:"America/Sao_Paulo",year:"numeric",month:"2-digit",day:"2-digit"}).format(clock);
}
function dateParts(clock) {
  const parts = new Intl.DateTimeFormat("en-US",{timeZone:"America/Sao_Paulo",year:"numeric",month:"2-digit",day:"2-digit"}).formatToParts(clock);
  const obj = Object.fromEntries(parts.map(x=>[x.type,x.value]));
  return Date.UTC(Number(obj.year),Number(obj.month)-1,Number(obj.day));
}
function statusBool(p, key) {
  const aliases = {
    aprovado:["aprovado","Aprovado"],
    pago:["pago","Pago"],
    pronto:["pronto","Pronto"],
    entregue:["entregue","Entregue"],
    cancelado_cliente:["cancelado_cliente","CanceladoCliente","cancelado_pelo_cliente"],
    encerrado:["encerrado","Encerrado"]
  }[key] || [key];
  for (const alias of aliases) {
    if (Object.prototype.hasOwnProperty.call(p,alias) && p[alias] !== null) return truthy(p[alias]);
  }
  return false;
}
function closed(p) {
  // Espelha a fonte unica em proposal_status.py: aliases e precedencia.
  if (statusBool(p,"cancelado_cliente")) return true;
  const status = String(p.status_comercial || p.situacao_comercial || p.status || "").trim().toLowerCase();
  const hard = new Set([
    "cancelado","cancelada","cancelado_cliente","cancelado pelo cliente","cancelada pelo cliente",
    "recusado","recusada","arquivado","arquivada","excluído","excluida","excluída"
  ]);
  if (hard.has(status)) return true;
  const commercial = truthy(p.nao_fechado_pagamento) || truthy(p.nao_fechado_sem_retorno) ||
    new Set([
      "encerrado","encerrada","encerrado sem retorno","encerrado por preço","encerrado por preco",
      "encerrado pelo cliente","encerrado por prazo","nao_fechado_pagamento",
      "não fechado — falta de pagamento","nao_fechado_sem_retorno","não fechado — sem retorno do cliente"
    ]).has(status);
  if (commercial && (statusBool(p,"pago") || statusBool(p,"pronto") || statusBool(p,"entregue"))) return false;
  return commercial || statusBool(p,"encerrado");
}
export function summarizeQuotes(document, clock = new Date()) {
  if (!Array.isArray(document)) throw new Error("Historico de propostas com formato inesperado");
  if (document.length > MAX_RECORDS) throw new Error("Historico excede limite seguro");
  const today = dateParts(clock);
  const counts = {pending:0, next:0, late:0, unknown:0, deliveryUrgent:0};
  for (const p of document) {
    if (!p || typeof p !== "object" || Array.isArray(p)) continue;
    if (!truthy(p.enviado) || statusBool(p,"aprovado") || statusBool(p,"entregue") || closed(p)) continue;
    counts.pending++;
    const last = dateOnly(p.ultimo_envio_em) ?? dateOnly(p.enviado_em) ?? dateOnly(p.data_geracao) ?? dateOnly(p.data);
    if (last === null) counts.unknown++;
    else {
      const days = Math.max(0,Math.floor((today-last)/86400000));
      if (days >= 3) counts.late++;
      else if (days >= 1) counts.next++;
    }
    const delivery = dateOnly(p.data_entrega);
    if (delivery !== null && delivery <= today+2*86400000) counts.deliveryUrgent++;
  }
  return counts;
}
export function formatSummary(c, clock = new Date()) {
  return [
    "📋 AlphaFest — resumo de retornos comerciais",
    "📅 "+brDate(clock),
    "📨 Orçamentos enviados e não aprovados: "+c.pending,
    "🔴 Último envio há 3+ dias: "+c.late,
    "🟡 Último envio há 1–2 dias: "+c.next,
    "📅 Prazo de entrega vencido ou até 2 dias: "+c.deliveryUrgent,
    "❓ Sem data confiável do último envio: "+c.unknown,
    "",
    "Conferir propostas no Manager antes de qualquer contato.",
    "Não são mensagens recebidas nem vendas; nenhuma ação foi feita automaticamente."
  ].join("\n");
}
export async function runDaily(env, fetcher = fetch, clock = new Date()) {
  if (String(env.QUOTE_SUMMARY_ENABLED || "").toLowerCase() !== "true") return {status:"disabled"};
  const base = String(env.SUPABASE_URL || "").replace(/\/+$/, "");
  const key = String(env.SUPABASE_SECRET_KEY || "");
  const token = String(env.TELEGRAM_BOT_TOKEN || "");
  const chat = String(env.TELEGRAM_CHAT_ID || "");
  if (!base.startsWith("https://") || !key || !token || !/^-?\d+$/.test(chat)) throw new Error("Configuracao incompleta");
  const url = new URL(base+"/rest/v1/app_data");
  url.searchParams.set("select","value");
  url.searchParams.set("key","eq.historico_orcamentos");
  url.searchParams.set("limit","1");
  const headers = {apikey:key,Accept:"application/json"};
  if (!key.startsWith("sb_secret_")) headers.Authorization="Bearer "+key;
  const response = await fetcher(url.toString(), {method:"GET",headers});
  if (!response.ok) throw new Error("Nao foi possivel consultar o Historico");
  const rows = await response.json();
  if (!Array.isArray(rows) || rows.length!==1 || !rows[0] || !Array.isArray(rows[0].value)) throw new Error("Historico ausente ou invalido");
  const counts = summarizeQuotes(rows[0].value,clock);
  // D1: reserva atomica por dia ANTES de enviar. At-most-once, nao exactly-once:
  // falha de rede apos reserva exige intervencao manual, nunca retry automatico.
  const db = env.QUOTE_DEDUPE_DB;
  if (!db || typeof db.prepare !== "function") throw new Error("D1 dedupe nao configurado; envio bloqueado");
  const dateKey = new Intl.DateTimeFormat("en-CA",{
    timeZone:"America/Sao_Paulo", year:"numeric",month:"2-digit",day:"2-digit"
  }).format(clock);
  const claimed = await db.prepare(
    "INSERT OR IGNORE INTO quote_summary_delivery(day_key, claimed_at) VALUES (?, ?)"
  ).bind(dateKey,clock.toISOString()).run();
  if (!claimed?.success) throw new Error("Falha ao reservar dia no D1");
  if (Number(claimed.meta?.changes || 0) === 0) return {status:"already-claimed"};
  const sent = await fetcher("https://api.telegram.org/bot"+token+"/sendMessage",{
    method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({chat_id:chat,text:formatSummary(counts,clock),disable_notification:true})
  });
  if (!sent.ok || (await sent.json())?.ok!==true) {
    // Nao libera a reserva: retry poderia duplicar se o Telegram recebeu.
    throw new Error("Envio nao confirmado; reserva mantida, verificar grupo antes de agir");
  }
  await db.prepare("UPDATE quote_summary_delivery SET confirmed_at = ? WHERE day_key = ?")
    .bind(new Date().toISOString(), dateKey).run().catch(() => {});
  return {status:"sent",counts};
}
export default {
  async fetch(){return new Response("Not found",{status:404,headers:{"Cache-Control":"no-store"}});},
  async scheduled(_event,env){return runDaily(env);}
};
