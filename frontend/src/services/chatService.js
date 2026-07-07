import api from "./api";

export async function iniciarSessao(email) {
  const resposta = await api.post("/chat/sessao", { email });
  return resposta.data;
}

export async function encerrarSessao(sessaoId, email) {
  const resposta = await api.delete(`/chat/sessao/${sessaoId}/encerrar`, { params: { email } });
  return resposta.data;
}

export async function excluirSessao(sessaoId, email) {
  // DELETE /chat/sessao/{id} — remove sessão, mensagens e chunks do banco
  const resposta = await api.delete(`/chat/sessao/${sessaoId}`, { params: { email } });
  return resposta.data;
}

export async function enviarPergunta(sessaoId, pergunta, email) {
  const resposta = await api.post(`/chat/sessao/${sessaoId}/perguntar`, { pergunta, email });
  return resposta.data;
}

export async function buscarHistorico(sessaoId, email) {
  const resposta = await api.get(`/chat/sessao/${sessaoId}/historico`, { params: { email } });
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