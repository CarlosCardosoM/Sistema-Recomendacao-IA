// Cadastro — passo 2 de 2. Confirma o código -> POST /alunos/verificar-cadastro
import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import PainelLateral from "../../components/PainelLateral";
import InputCodigo from "../../components/InputCodigo";
import ContadorExpiracao from "../../components/ContadorExpiracao";
import { verificarCadastro, cadastrarAluno } from "../../services/authService";
import "./Auth.css";

export default function VerificarCadastro() {
  const localizacao = useLocation();
  const navegar = useNavigate();
  const email = localizacao.state?.email;

  const [codigo, setCodigo] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");
  const [sucesso, setSucesso] = useState(false);
  const [chaveReenvio, setChaveReenvio] = useState(0);
  const [expirado, setExpirado] = useState(false);

  if (!email) {
    navegar("/cadastro");
    return null;
  }

  async function aoConfirmar(evento) {
    evento.preventDefault();
    setErro("");
    setCarregando(true);
    try {
      await verificarCadastro({ email, token: codigo });
      setSucesso(true);
      setTimeout(() => navegar("/entrar"), 1800);
    } catch (erroRequisicao) {
      setErro(erroRequisicao.response?.data?.detail || "Código inválido. Tente novamente.");
    } finally {
      setCarregando(false);
    }
  }

  async function aoReenviar() {
    setErro("");
    try {
      await cadastrarAluno({ nome: "", email });
      setExpirado(false);
      setChaveReenvio((atual) => atual + 1);
    } catch {
      setErro("Não foi possível reenviar o código.");
    }
  }

  return (
    <div className="tela-auth">
      <PainelLateral titulo="Quase lá!" texto="Confirme seu e-mail para começar a estudar com a SabiÁ." />
      <div className="tela-auth__formulario">
        <div className="tela-auth__card">
          <p className="tela-auth__etapa">cadastro — passo 2 de 2</p>
          <h2>Confirme seu e-mail</h2>
          <p className="tela-auth__subtitulo">
            Digite o código de 6 dígitos enviado para <br /><strong>{email}</strong>
          </p>

          {erro && <div className="erro-formulario">{erro}</div>}
          {sucesso && <div className="sucesso-formulario">Cadastro confirmado! Redirecionando para o login...</div>}

          <form onSubmit={aoConfirmar}>
            <InputCodigo onChange={setCodigo} />
            <ContadorExpiracao onExpirar={() => setExpirado(true)} reiniciarChave={chaveReenvio} />
            <button type="submit" className="botao-primario" disabled={carregando || codigo.length < 6 || expirado || sucesso}>
              {carregando ? "Confirmando..." : "Confirmar cadastro ✓"}
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
