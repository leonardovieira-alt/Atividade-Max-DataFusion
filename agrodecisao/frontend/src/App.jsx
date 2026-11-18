import { useEffect, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, ComposedChart, Legend, Line,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { api } from "./api.js";

const ICONES = { geada: "❄️", pulverizacao: "💧", deficit_hidrico: "🏜️", colheita: "🚜" };
const brl = (v) => Number(v).toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
const dm = (s) => s.slice(8, 10) + "/" + s.slice(5, 7);

export default function App() {
  const [talhoes, setTalhoes] = useState([]);
  const [resumo, setResumo] = useState([]);
  const [sel, setSel] = useState(null);
  const [clima, setClima] = useState([]);
  const [recs, setRecs] = useState([]);
  const [cot, setCot] = useState(null);
  const [margem, setMargem] = useState([]);
  const [msg, setMsg] = useState("");

  const carregarBase = async () => {
    try {
      const [t, r, c, m] = await Promise.all([api.talhoes(), api.resumo(), api.cotacoes(), api.margem()]);
      setTalhoes(t); setResumo(r); setCot(c); setMargem(m);
      setSel((s) => s ?? t[0]?.id);
    } catch (e) { setMsg("Erro ao carregar dados: " + e.message); }
  };

  useEffect(() => { carregarBase(); }, []);

  useEffect(() => {
    if (!sel) return;
    Promise.all([api.clima(sel), api.recomendacoes(sel)])
      .then(([c, r]) => { setClima(c); setRecs(r); })
      .catch((e) => setMsg(e.message));
  }, [sel]);

  const sincronizar = async () => {
    setMsg("Sincronizando clima (Open-Meteo → MongoDB → PostgreSQL)...");
    try {
      const r = await api.sincronizar();
      const falhas = Object.values(r).filter((x) => !x.ok).length;
      setMsg(falhas ? `Sincronização concluída com ${falhas} falha(s).` : "Clima atualizado com sucesso.");
      await carregarBase();
      if (sel) { setClima(await api.clima(sel)); setRecs(await api.recomendacoes(sel)); }
    } catch (e) { setMsg("Falha na sincronização: " + e.message); }
  };

  const talhao = talhoes.find((t) => t.id === sel);
  const margemSel = margem.filter((m) => m.talhao_id === sel);

  return (
    <div className="app">
      <header>
        <div>
          <h1>🌱 AgroDecisão</h1>
          <p>Clima + mercado + histórico da lavoura em uma única decisão</p>
        </div>
        <button onClick={sincronizar}>Atualizar clima</button>
      </header>
      {msg && <div className="msg">{msg}</div>}

      <section className="cards">
        {resumo.map((r) => (
          <div key={r.talhao_id} className={`card ${sel === r.talhao_id ? "ativo" : ""}`}
               onClick={() => setSel(r.talhao_id)}>
            <b>{r.nome}</b>
            <span className="tag">{r.cultura}</span>
            <div className={r.alertas ? "alerta" : "ok"}>
              {r.alertas ? `${r.alertas} alerta(s)` : "Sem alertas"}
            </div>
            {r.proximo && <small>{r.proximo.mensagem}</small>}
          </div>
        ))}
      </section>

      {talhao && (
        <>
          <h2>{talhao.nome} · {talhao.area_ha} ha</h2>
          <div className="grid">
            <section className="painel">
              <h3>Recomendações</h3>
              {recs.length === 0 && <p>Nenhuma recomendação para os próximos dias.</p>}
              <ul className="recs">
                {recs.map((r, i) => (
                  <li key={i} className={r.severidade}>
                    <span>{ICONES[r.tipo]}</span>
                    <div><b>{dm(r.data)}</b> — {r.mensagem}</div>
                  </li>
                ))}
              </ul>
            </section>

            <section className="painel">
              <h3>Clima (7 dias passados + 7 de previsão)</h3>
              {clima.length === 0 ? <p>Sem dados. Clique em “Atualizar clima”.</p> : (
                <ResponsiveContainer width="100%" height={260}>
                  <ComposedChart data={clima.map((c) => ({ ...c, dia: dm(c.data) }))}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="dia" fontSize={11} />
                    <YAxis yAxisId="t" unit="°" fontSize={11} />
                    <YAxis yAxisId="c" orientation="right" unit="mm" fontSize={11} />
                    <Tooltip /><Legend />
                    <Bar yAxisId="c" dataKey="chuva_mm" name="Chuva (mm)" fill="#4a90d9" />
                    <Line yAxisId="t" dataKey="tmax" name="Máx" stroke="#e5732f" dot={false} />
                    <Line yAxisId="t" dataKey="tmin" name="Mín" stroke="#2f7de5" dot={false} />
                  </ComposedChart>
                </ResponsiveContainer>
              )}
            </section>

            <section className="painel">
              <h3>Margem por safra (R$/ha, preço atual)</h3>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={margemSel}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="safra" fontSize={11} />
                  <YAxis fontSize={11} />
                  <Tooltip formatter={(v) => brl(v)} /><Legend />
                  <Bar dataKey="receita_ha" name="Receita" fill="#5aa469" />
                  <Bar dataKey="custo_ha" name="Custo" fill="#c0504d" />
                  <Bar dataKey="margem_ha" name="Margem" fill="#2d6a4f" />
                </BarChart>
              </ResponsiveContainer>
            </section>

            <section className="painel">
              <h3>Mercado</h3>
              {cot?.dolar
                ? <p>Dólar: <b>R$ {cot.dolar.valor.toFixed(2)}</b> ({cot.dolar.variacao_pct}%)</p>
                : <p>Dólar indisponível no momento.</p>}
              <table>
                <thead><tr><th>Produto</th><th>Preço</th><th>Unidade</th><th>Data</th></tr></thead>
                <tbody>
                  {cot?.ultimas.map((c) => (
                    <tr key={c.produto}>
                      <td>{c.produto}</td><td>{brl(c.preco)}</td><td>{c.unidade}</td><td>{dm(c.data)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          </div>
        </>
      )}
    </div>
  );
}
