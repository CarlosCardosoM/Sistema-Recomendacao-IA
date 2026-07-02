import api from "./api";

export async function iniciarSessao(email) {
  const resposta = await api.post("/chat/sessao", { email });
  return resposta.data;
}

export async function encerrarSessao(sessaoId) {
  const resposta = await api.delete(`/chat/sessao/${sessaoId}/encerrar`);
  return resposta.data;
}

export async function excluirSessao(sessaoId) {
  // DELETE /chat/sessao/{id} — remove sessão, mensagens e chunks do banco
  const resposta = await api.delete(`/chat/sessao/${sessaoId}`);
  return resposta.data;
}

export async function enviarPergunta(sessaoId, pergunta) {
  const resposta = await api.post(`/chat/sessao/${sessaoId}/perguntar`, { pergunta });
  return resposta.data;
}

export async function buscarHistorico(sessaoId) {
  const resposta = await api.get(`/chat/sessao/${sessaoId}/historico`);
  return resposta.data;
}

export async function abrirConteudo(email, conteudo_id) {
  const resposta = await api.post("/interacoes/abrir", { email, conteudo_id });
  return resposta.data;
}

export async function fecharConteudo(interacaoId) {
  const resposta = await api.put(`/interacoes/${interacaoId}/fechar`);
  return resposta.data;
}