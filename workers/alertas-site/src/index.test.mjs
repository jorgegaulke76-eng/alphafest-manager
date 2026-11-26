import test from "node:test";
import assert from "node:assert/strict";
import {windowFor, isTechnicalPath, summarizeRows, formatAlert, executeAlert, supabaseRequest} from "./index.mjs";

const env = {
  ALERTS_ENABLED: "true",
  SUPABASE_URL: "https://demo.supabase.co",
  SUPABASE_SECRET_KEY: "sb_secret_FICTICIO",
  TELEGRAM_BOT_TOKEN: "TOKEN_FICTICIO",
  TELEGRAM_CHAT_ID: "-1001234567"
};
const date = Date.parse("2026-11-26T22:20:00.000Z");
const period = windowFor(date);

test("janela fixa de cinco minutos, sem sobreposição", () => {
  assert.equal(period.start.toISOString(), "2026-11-26T22:15:00.000Z");
  assert.equal(period.end.toISOString(), "2026-11-26T22:20:00.000Z");
  const next = windowFor(date + 300000);
  assert.equal(next.start.toISOString(), period.end.toISOString());
});

test("filtra URLs técnicas; não afirma identificação real", () => {
  assert.equal(isTechnicalPath("/robots.txt"), true);
  assert.equal(isTechnicalPath("/cdn-cgi/trace"), true);
  assert.equal(isTechnicalPath("/produtos/"), false);
  const s = summarizeRows([
    {event_type:"page_view", page_path:"/", session_id:"A"},
    {event_type:"page_view", page_path:"/produtos/", session_id:"A"},
    {event_type:"page_view", page_path:"/galeria/", session_id:"B"},
    {event_type:"page_view", page_path:"/robots.txt", session_id:"C"},
    {event_type:"product_open", page_path:"/", session_id:"B"},
    {event_type:"whatsapp_click", page_path:"/", session_id:"B"}
  ]);
  assert.equal(s.pageViews, 3);
  assert.equal(s.sessions, 2);
  assert.equal(s.opened, 1);
  assert.equal(s.whatsapp, 1);
  assert.match(formatAlert(s, period), /Acessos registrados: 3/);
});

test("desativado nunca faz rede e não exige segredos", async () => {
  const r = await executeAlert(date, {ALERTS_ENABLED:"false"}, async () => {throw Error("rede proibida");});
  assert.equal(r.status, "disabled");
});

test("sem eventos não envia mensagem", async () => {
  let calls = 0;
  const r = await executeAlert(date, env, async () => {calls++; return {ok:true,json:async()=>[]};});
  assert.equal(calls, 1);
  assert.equal(r.status, "no-activity");
});

test("envia somente totais sem dados pessoais nem tokens na mensagem", async () => {
  const calls = [];
  const r = await executeAlert(date, env, async (url, options) => {
    calls.push({url,options});
    if (calls.length===1) return {ok:true,json:async()=>[
      {event_type:"page_view",page_path:"/privado?email=ana@example.com",session_id:"identificador_sigilo"},
      {event_type:"whatsapp_click",page_path:"/",session_id:"identificador_sigilo"}
    ]};
    return {ok:true,json:async()=>({ok:true})};
  });
  assert.equal(r.status,"sent");
  assert.equal(calls.length,2);
  assert.match(calls[0].url, /site_metrics_events/);
  assert.equal(calls[0].options.init?.headers?.Authorization,undefined);
  const body=JSON.parse(calls[1].options.body);
  assert.equal(body.chat_id, env.TELEGRAM_CHAT_ID);
  assert.equal(body.disable_notification, false);
  for(const secret of ["identificador_sigilo", "ana@example.com",env.SUPABASE_SECRET_KEY,env.TELEGRAM_BOT_TOKEN]) {
    assert.equal(body.text.includes(secret),false);
  }
});

test("falta de chave ou falha na leitura bloqueia envio", async () => {
  await assert.rejects(executeAlert(date, {...env, TELEGRAM_BOT_TOKEN:""}, async()=>null),/Telegram secrets/);
  await assert.rejects(executeAlert(date, env, async()=>({ok:false,status:401})),/reading website metrics/);
});

test("consulta PostgREST usa filtros exclusivos da janela", () => {
  const {url}=supabaseRequest(env,period);
  const p=new URL(url).searchParams;
  const bounds=p.getAll("created_at");
  assert.equal(bounds.length,2);
  assert.ok(bounds[0].startsWith("gte."));
  assert.ok(bounds[1].startsWith("lt."));
  assert.equal(p.get("limit"),"1000");
});
