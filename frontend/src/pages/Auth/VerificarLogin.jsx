// Login — passo 2 de 2. Verifica o código via POST /alunos/login/verificar
import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import PainelLateral from "../../components/PainelLateral";
import InputCodigo from "../../components/InputCodigo";
import ContadorExpiracao from "../../components/ContadorExpiracao";
import { verificarLogin, solicitarLogin } from "../../services/authService";
import { useAuth } from "../../context/AuthContext";
import "./Auth.css";

export default function VerificarLogin() {
  const localizacao = useLocation();
  const navegar = useNavigate();
  const { login } = useAuth();
  const email = localizacao.state?.email;

  const [codigo, setCodigo] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");
  const [chaveReenvio, setChaveReenvio] = useState(0);
  const [expirado, setExpirado] = useState(false);

  if (!email) {
    navegar("/entrar");
    return null;
  }

  async function aoConfirmar(evento) {
    evento.preventDefault();
    setErro("");
    setCarregando(true);
    try {
      const aluno = await verificarLogin({ email, token: codigo });
      login(aluno);
      navegar("/chat");
    } catch (erroRequisicao) {
      setErro(erroRequisicao.response?.data?.detail || "Código inválido. Tente novamente.");
    } finally {
      setCarregando(false);
    }
  }

  async function aoReenviar() {
    setErro("");
    try {
      await solicitarLogin({ email });
      setExpirado(false);
      setChaveReenvio((atual) => atual + 1);
    } catch {
      setErro("Não foi possível reenviar o código. Tente novamente em breve.");
    }
  }

  return (
    <div className="tela-auth">
      <PainelLateral titulo="Verifique seu e-mail" texto="Enviamos um código de acesso para garantir que é realmente você." />
      <div className="tela-auth__formulario">
        <div className="tela-auth__card">
          <p className="tela-auth__etapa">login — passo 2 de 2</p>
          <h2>Digite o código</h2>
          <p className="tela-auth__subtitulo">
            Enviamos um código de 6 dígitos para <br /><strong>{email}</strong>
          </p>

          {erro && <div className="erro-formulario">{erro}</div>}

          <form onSubmit={aoConfirmar}>
            <InputCodigo onChange={setCodigo} />
            <ContadorExpiracao onExpirar={() => setExpirado(true)} reiniciarChave={chaveReenvio} />
            <button type="submit" className="botao-primario" disabled={carregando || codigo.length < 6 || expirado}>
              {carregando ? "Verificando..." : "Confirmar ✓"}
            </button>
          </form>

          <p className="tela-auth__rodape-link">
            <button type="button" onClick={aoReenviar} className="link-botao">Reenviar código</button>
          </p>
        </div>
      </div>
    </div>
  );
}
