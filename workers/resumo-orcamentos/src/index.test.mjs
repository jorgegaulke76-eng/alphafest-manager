import test from "node:test";
import assert from "node:assert/strict";
import {summarizeQuotes,formatSummary,runDaily} from "./index.mjs";

const clock = new Date("2026-11-27T12:00:00Z");

test("conta apenas propostas enviadas, abertas e reais", () => {
  const data = [
    {enviado:true,ultimo_envio_em:"24/11/2026"},
    {enviado:true,ultimo_envio_em:"26/11/2026"},
    {enviado:true,ultimo_envio_em:"26/11/2026",aprovado:true},
    {enviado:true,ultimo_envio_em:"24/11/2026",cancelado_cliente:true},
    {enviado:true,ultimo_envio_em:"24/11/2026",status_comercial:"recusado"},
    {enviado:false,ultimo_envio_em:"24/11/2026"},
  ];
  assert.deepEqual(summarizeQuotes(data,clock),{
    pending:2,actionable:2,highPriority:1,waiting:0,next:1,late:1,unknown:0,deliveryUrgent:0
  });
});

test("contagens de acao, prioridade e espera seguem criterio do THU",()=> {
  const data = [
    {enviado:true,ultimo_envio_em:"27/11/2026"},
    {enviado:true,ultimo_envio_em:"26/11/2026"},
    {enviado:true,ultimo_envio_em:"24/11/2026"},
    {enviado:true,ultimo_envio_em:"27/11/2026",data_entrega:"28/11/2026"},
    {enviado:true,ultimo_envio_em:"26/11/2026",data_entrega:"25/11/2026"},
    {enviado:true,ultimo_envio_em:"27/11/2026",aprovado:true},
  ];
  assert.deepEqual(summarizeQuotes(data,clock),{
    pending:5,actionable:4,highPriority:3,waiting:1,next:2,late:1,unknown:0,deliveryUrgent:2
  });
  const message=formatSummary(summarizeQuotes(data,clock),clock);
  assert.match(message,/Retornos a conferir: 4/);
  assert.match(message,/Prioridade alta ou urgente: 3/);
  assert.match(message,/Aguardando cliente: 1/);
});

test("status comercial obsoleto nao encerra pedido que progrediu",()=>{
  assert.equal(summarizeQuotes([
    {enviado:true,nao_fechado_sem_retorno:true,pago:true},
    {enviado:true,encerrado:true,status_comercial:"cancelado",pago:true},
  ],clock).pending,1);
});

test("texto agregado nao expõe dados particulares",()=>{
  const data = [{enviado:true,cliente_nome:"Nome Confidencial",whatsapp:"11999999999",
    numero_proposta:"SECRET123",total:"R$ 9.999",ultimo_envio_em:"24/11/2026"}];
  const message = formatSummary(summarizeQuotes(data,clock),clock);
  for(const secret of ["Nome Confidencial","11999999999","SECRET123","9.999"]) {
    assert.equal(message.includes(secret),false);
  }
});

test("sem D1, falha antes de enviar",async()=>{
  const env={QUOTE_SUMMARY_ENABLED:"true",SUPABASE_URL:"https://example.supabase.co",
    SUPABASE_SECRET_KEY:"fake",TELEGRAM_BOT_TOKEN:"fake",TELEGRAM_CHAT_ID:"-123"};
  let calls=0;
  const fetcher=async()=>{calls++;return {ok:true,json:async()=>[{value:[]}]};};
  await assert.rejects(runDaily(env,fetcher,clock),/D1 dedupe nao configurado/);
  assert.equal(calls,1);
});

test("reserva unica impede reenvio no mesmo dia",async()=>{
  let claimed=false, messages=0;
  const db={prepare(sql){return {
    bind(){return {async run(){
      if(sql.startsWith("INSERT")) {
        const changes=claimed?0:1;
        claimed=true;
        return {success:true,meta:{changes}};
      }
      return {success:true};
    }}}
  }}};
  const env={QUOTE_SUMMARY_ENABLED:"true",SUPABASE_URL:"https://example.supabase.co",
    SUPABASE_SECRET_KEY:"fake",TELEGRAM_BOT_TOKEN:"fake",TELEGRAM_CHAT_ID:"-123",
    QUOTE_DEDUPE_DB:db};
  const fetcher=async(url)=>{
    if(url.includes("telegram")){messages++;return {ok:true,json:async()=>({ok:true})};}
    return {ok:true,json:async()=>[{value:[]}]};
  };
  assert.equal((await runDaily(env,fetcher,clock)).status,"sent");
  assert.equal((await runDaily(env,fetcher,clock)).status,"already-claimed");
  assert.equal(messages,1);
});
