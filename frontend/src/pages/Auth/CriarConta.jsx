import { useState } from "react";
import { useNavigate } from "react-router-dom";
import PainelLateral from "../../components/PainelLateral";
import { cadastrarAluno } from "../../services/authService";
import "./Auth.css";

const TIPOS_MIDIA = ["Vídeo", "Artigo", "Código", "Livro", "Exercício"];

export default function CriarConta() {
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [preferencias, setPreferencias] = useState([]);
  const [aceitouTermos, setAceitouTermos] = useState(false);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");
  const navegar = useNavigate();

  function togglePreferencia(tipo) {
    setPreferencias((atual) =>
      atual.includes(tipo)
        ? atual.filter((t) => t !== tipo)
        : [...atual, tipo]
    );
  }

  async function aoEnviar(evento) {
    evento.preventDefault();
    setErro("");

    if (!aceitouTermos) {
      setErro("Você precisa aceitar os Termos de Uso para continuar.");
      return;
    }

    setCarregando(true);
    try {
      await cadastrarAluno({
        nome,
        email,
        preferencias_tipos: preferencias.join(",") || null,
      });
      navegar("/verificar-cadastro", { state: { email } });
    } catch (erroRequisicao) {
      setErro(
        erroRequisicao.response?.data?.detail ||
          "Não foi possível criar a conta. E-mail já cadastrado. Tente novamente."
      );
    } finally {
      setCarregando(false);
    }
  }

  return (
    <div className="tela-auth">
      <PainelLateral
        titulo="Criar conta"
        texto="Crie sua conta e tenha acesso a um mundo de conhecimento personalizado para você."
      />
      <div className="tela-auth__formulario">
        <div className="tela-auth__card">
          <h2>Criar conta</h2>
          <p className="tela-auth__subtitulo">Preencha os dados para se cadastrar</p>

          {erro && <div className="erro-formulario">{erro}</div>}

          <form onSubmit={aoEnviar}>
            <div className="campo">
              <label htmlFor="nome">Nome completo</label>
              <input
                id="nome"
                type="text"
                placeholder="Seu nome completo"
                value={nome}
                onChange={(e) => setNome(e.target.value)}
                required
                autoFocus
              />
            </div>

            <div className="campo">
              <label htmlFor="email">E-mail</label>
              <input
                id="email"
                type="email"
                placeholder="seu@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <div className="campo">
              <label>Preferências de conteúdo</label>
              <div className="preferencias-grid">
                {TIPOS_MIDIA.map((tipo) => (
                  <button
                    key={tipo}
                    type="button"
                    className={`preferencia-item ${preferencias.includes(tipo) ? "ativo" : ""}`}
                    onClick={() => togglePreferencia(tipo)}
                  >
                    {tipo}
                  </button>
                ))}
              </div>
            </div>

            <label className="checkbox-termos">
              <input
                type="checkbox"
                checked={aceitouTermos}
                onChange={(e) => setAceitouTermos(e.target.checked)}
              />
              <span>
                Eu concordo com os <a href="/termos">Termos de Uso</a> e a{" "}
                <a href="/privacidade">Política de Privacidade</a>
              </span>
            </label>

            <button type="submit" className="botao-primario" disabled={carregando}>
              {carregando ? "Enviando..." : "Enviar código →"}
            </button>
          </form>

          <p className="tela-auth__rodape-link">
            Já tem uma conta? <a href="/entrar">Entrar</a>
          </p>
        </div>
      </div>
    </div>
  );
}