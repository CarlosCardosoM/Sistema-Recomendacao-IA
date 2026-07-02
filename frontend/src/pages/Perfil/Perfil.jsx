import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import {
  atualizarEmail,
  atualizarPreferencias,
  excluirConta,
} from "../../services/perfilService";
import { ArrowLeft, User, Mail, Tag, Trash2, Save, X } from "lucide-react";
import "./Perfil.css";

const TIPOS_MIDIA = ["Vídeo", "Artigo", "Código", "Livro", "Exercício"];

export default function Perfil() {
  const { aluno, login, logout } = useAuth();
  const navegar = useNavigate();

  // Estado dos campos editáveis
  const [novoEmail, setNovoEmail] = useState(aluno?.email || "");
  const [preferencias, setPreferencias] = useState(
    aluno?.preferencias_tipos ? aluno.preferencias_tipos.split(",") : []
  );

  // Estado de feedback
  const [carregandoEmail, setCarregandoEmail] = useState(false);
  const [carregandoPref, setCarregandoPref] = useState(false);
  const [erroEmail, setErroEmail] = useState("");
  const [erroPref, setErroPref] = useState("");
  const [sucessoEmail, setSucessoEmail] = useState("");
  const [sucessoPref, setSucessoPref] = useState("");

  // Modal de confirmação de exclusão
  const [modalExcluir, setModalExcluir] = useState(false);
  const [carregandoExcluir, setCarregandoExcluir] = useState(false);
  const [erroExcluir, setErroExcluir] = useState("");

  function togglePreferencia(tipo) {
    setPreferencias((atual) =>
      atual.includes(tipo)
        ? atual.filter((t) => t !== tipo)
        : [...atual, tipo]
    );
  }

  async function aoSalvarEmail(evento) {
    evento.preventDefault();
    setErroEmail("");
    setSucessoEmail("");

    if (novoEmail === aluno.email) {
      setErroEmail("O e-mail informado é igual ao atual.");
      return;
    }

    setCarregandoEmail(true);
    try {
      const atualizado = await atualizarEmail(aluno.email, novoEmail);
      // Atualiza o aluno no contexto com o novo e-mail
      login({ ...aluno, email: novoEmail });
      setSucessoEmail("E-mail atualizado com sucesso!");
    } catch (erro) {
      setErroEmail(
        erro.response?.data?.detail || "Não foi possível atualizar o e-mail."
      );
    } finally {
      setCarregandoEmail(false);
    }
  }

  async function aoSalvarPreferencias(evento) {
    evento.preventDefault();
    setErroPref("");
    setSucessoPref("");
    setCarregandoPref(true);

    try {
      await atualizarPreferencias(aluno.email, preferencias.join(","));
      login({ ...aluno, preferencias_tipos: preferencias.join(",") });
      setSucessoPref("Preferências atualizadas com sucesso!");
    } catch (erro) {
      setErroPref(
        erro.response?.data?.detail || "Não foi possível atualizar as preferências."
      );
    } finally {
      setCarregandoPref(false);
    }
  }

  async function aoExcluirConta() {
    setErroExcluir("");
    setCarregandoExcluir(true);
    try {
      await excluirConta(aluno.email);
      logout();
      navegar("/entrar");
    } catch (erro) {
      setErroExcluir(
        erro.response?.data?.detail || "Não foi possível excluir a conta."
      );
    } finally {
      setCarregandoExcluir(false);
    }
  }

  return (
    <div className="tela-perfil">

      {/* ── Cabeçalho ── */}
      <header className="perfil-header">
        <button className="perfil-header__voltar" onClick={() => navegar("/chat")}>
          <ArrowLeft size={18} />
          <span>Voltar ao chat</span>
        </button>
        <div>
          <h1 className="perfil-header__titulo">Minha conta</h1>
          <p className="perfil-header__subtitulo">Gerencie suas informações pessoais</p>
        </div>

        <div className="perfil-header__avatar-nome">
          <div className="avatar-grande">
            {aluno?.nome?.split(" ").slice(0, 2).map((p) => p[0]).join("").toUpperCase()}
          </div>
          <div>
            <p className="perfil-header__nome">{aluno?.nome}</p>
            <p className="perfil-header__email-atual">{aluno?.email}</p>
          </div>
        </div>
      </header>

      <div className="perfil-conteudo">

        {/* ── Card: Alterar e-mail ── */}
        <div className="perfil-card">
          <div className="perfil-card__titulo">
            <Mail size={18} color="#2563eb" />
            <span>Alterar e-mail</span>
          </div>

          {erroEmail && <div className="erro-formulario">{erroEmail}</div>}
          {sucessoEmail && <div className="sucesso-formulario">{sucessoEmail}</div>}

          <form onSubmit={aoSalvarEmail}>
            <div className="campo">
              <label htmlFor="novo-email">Novo e-mail</label>
              <input
                id="novo-email"
                type="email"
                value={novoEmail}
                onChange={(e) => setNovoEmail(e.target.value)}
                placeholder="novo@email.com"
                required
              />
            </div>
            <div className="perfil-card__acoes">
              <button
                type="button"
                className="btn-secundario"
                onClick={() => setNovoEmail(aluno?.email || "")}
              >
                <X size={15} />
                Cancelar
              </button>
              <button
                type="submit"
                className="btn-primario-sm"
                disabled={carregandoEmail}
              >
                <Save size={15} />
                {carregandoEmail ? "Salvando..." : "Salvar e-mail"}
              </button>
            </div>
          </form>
        </div>

        {/* ── Card: Preferências ── */}
        <div className="perfil-card">
          <div className="perfil-card__titulo">
            <Tag size={18} color="#2563eb" />
            <span>Preferências de aprendizado</span>
          </div>
          <p className="perfil-card__descricao">
            Selecione os tipos de conteúdo que você prefere receber como recomendação.
          </p>

          {erroPref && <div className="erro-formulario">{erroPref}</div>}
          {sucessoPref && <div className="sucesso-formulario">{sucessoPref}</div>}

          <form onSubmit={aoSalvarPreferencias}>
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

            <div className="perfil-card__acoes">
              <button
                type="button"
                className="btn-secundario"
                onClick={() =>
                  setPreferencias(
                    aluno?.preferencias_tipos
                      ? aluno.preferencias_tipos.split(",")
                      : []
                  )
                }
              >
                <X size={15} />
                Cancelar
              </button>
              <button
                type="submit"
                className="btn-primario-sm"
                disabled={carregandoPref}
              >
                <Save size={15} />
                {carregandoPref ? "Salvando..." : "Salvar preferências"}
              </button>
            </div>
          </form>
        </div>

        {/* ── Card: Zona de perigo ── */}
        <div className="perfil-card perfil-card--perigo">
          <div className="perfil-card__titulo">
            <Trash2 size={18} color="#dc2626" />
            <span style={{ color: "#dc2626" }}>Excluir conta</span>
          </div>
          <p className="perfil-card__descricao">
            Ao excluir sua conta, todos os seus dados, histórico de conversas e
            interações serão permanentemente removidos. Esta ação não pode ser desfeita.
          </p>
          <button
            className="btn-perigo"
            onClick={() => setModalExcluir(true)}
          >
            <Trash2 size={15} />
            Excluir minha conta
          </button>
        </div>

      </div>

      {/* ── Modal de confirmação de exclusão ── */}
      {modalExcluir && (
        <div className="modal-overlay" onClick={() => setModalExcluir(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Excluir conta</h3>
            <p>
              Tem certeza que deseja excluir sua conta? Todos os seus dados serão
              permanentemente removidos e esta ação <strong>não pode ser desfeita</strong>.
            </p>

            {erroExcluir && <div className="erro-formulario">{erroExcluir}</div>}

            <div className="modal__acoes">
              <button
                className="btn-secundario"
                onClick={() => setModalExcluir(false)}
                disabled={carregandoExcluir}
              >
                Cancelar
              </button>
              <button
                className="btn-perigo"
                onClick={aoExcluirConta}
                disabled={carregandoExcluir}
              >
                {carregandoExcluir ? "Excluindo..." : "Sim, excluir conta"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
