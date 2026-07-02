// perfilService.js — espelha os endpoints do aluno_router.py
import api from "./api";

// PUT /alunos/{email}/email
export async function atualizarEmail(emailAtual, novoEmail) {
  const resposta = await api.put(`/alunos/${emailAtual}/email`, {
    novo_email: novoEmail,
  });
  return resposta.data;
}

// PUT /alunos/{email}/preferencias
export async function atualizarPreferencias(email, preferencias_tipos) {
  const resposta = await api.put(`/alunos/${email}/preferencias`, {
    preferencias_tipos,
  });
  return resposta.data;
}

// DELETE /alunos/{email}
export async function excluirConta(email) {
  const resposta = await api.delete(`/alunos/${encodeURIComponent(email)}`);
  return resposta.data;
}
