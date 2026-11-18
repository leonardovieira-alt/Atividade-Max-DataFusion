async function req(path, opts) {
  const r = await fetch(`/api${path}`, opts);
  if (!r.ok) throw new Error(`${r.status} ${path}`);
  return r.json();
}

export const api = {
  resumo: () => req("/resumo"),
  talhoes: () => req("/talhoes"),
  clima: (id) => req(`/talhoes/${id}/clima`),
  recomendacoes: (id) => req(`/talhoes/${id}/recomendacoes`),
  cotacoes: () => req("/cotacoes"),
  margem: () => req("/analytics/margem"),
  sincronizar: () => req("/etl/clima", { method: "POST" }),
};
