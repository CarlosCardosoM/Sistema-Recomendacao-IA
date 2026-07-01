// Login — passo 1 de 2. Aluno informa e-mail, chama POST /alunos/login
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import PainelLateral from "../../components/PainelLateral";
import { solicitarLogin } from "../../services/authService";
import "./Auth.css";

export default function Entrar() {
  const [email, setEmail] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");
  const navegar = useNavigate();

  async function aoEnviar(evento) {
    evento.preventDefault();
    setErro("");
    setCarregando(true);
    try {
      await solicitarLogin({ email });
      navegar("/verificar-login", { state: { email } });
    } catch (erroRequisicao) {
      setErro(erroRequisicao.response?.data?.detail || "Não foi possível enviar o código. Verifique o e-mail informado.");
    } finally {
      setCarregando(false);
    }
  }

  return (
    <div className="tela-auth">
      <PainelLateral
        titulo="Bem-vindo!"
        texto="Estamos aqui para ajudar você a aprender, evoluir e alcançar seus objetivos acadêmicos."
      />
      <div className="tela-auth__formulario">
        <div className="tela-auth__card">
          <h2>Entrar</h2>
          <p className="tela-auth__subtitulo">Informe seu e-mail para receber um código de acesso</p>

          {erro && <div className="erro-formulario">{erro}</div>}

          <form onSubmit={aoEnviar}>
            <div className="campo">
              <label htmlFor="email">E-mail</label>
              <input id="email" type="email" placeholder="seu@email.com" value={email}
                onChange={(e) => setEmail(e.target.value)} required autoFocus />
            </div>
            <button type="submit" className="botao-primario" disabled={carregando}>
              {carregando ? "Enviando..." : "Enviar código →"}
            </button>
          </form>

          <p className="tela-auth__rodape-link">
            Não tem uma conta? <a href="/cadastro">Cadastre-se</a>
          </p>
        </div>
      </div>
    </div>
  );
}
