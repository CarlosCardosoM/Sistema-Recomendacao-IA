// chatService.js — espelha os endpoints do chat_router.py
import api from "./api";

// POST /chat/sessao — inicia uma nova sessão
export async function iniciarSessao(email) {
  const resposta = await api.post("/chat/sessao", { email });
  return resposta.data; // { sessao_id, mensagem, data_hora_inicio }
}

// DELETE /chat/sessao/{id} — encerra a sessão
export async function encerrarSessao(sessaoId) {
  const resposta = await api.delete(`/chat/sessao/${sessaoId}`);
  return resposta.data;
}

// POST /chat/sessao/{id}/perguntar — envia pergunta, recebe resposta + recomendações
export async function enviarPergunta(sessaoId, pergunta) {
  const resposta = await api.post(`/chat/sessao/${sessaoId}/perguntar`, { pergunta });
  return resposta.data;
  // { resposta, analise_pergunta, conteudos_relevantes, recomendacoes }
}

// GET /chat/sessao/{id}/historico — busca histórico de mensagens
export async function buscarHistorico(sessaoId) {
  const resposta = await api.get(`/chat/sessao/${sessaoId}/historico`);
  return resposta.data;
}
