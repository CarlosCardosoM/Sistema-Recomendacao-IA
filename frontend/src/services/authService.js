// Espelha 1:1 os endpoints do aluno_router.py
import api from "./api";

export async function cadastrarAluno({ nome, email, preferencias_tipos }) {
  const resposta = await api.post("/alunos/", {
    nome,
    email,
    preferencias_tipos: preferencias_tipos || null,
  });
  return resposta.data;
}

export async function verificarCadastro({ email, token }) {
  const resposta = await api.post("/alunos/verificar-cadastro", { email, token });
  return resposta.data;
}

export async function solicitarLogin({ email }) {
  const resposta = await api.post("/alunos/login", { email });
  return resposta.data;
}

export async function verificarLogin({ email, token }) {
  const resposta = await api.post("/alunos/login/verificar", { email, token });
  return resposta.data;
}
