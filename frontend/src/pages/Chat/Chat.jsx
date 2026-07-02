import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import {
  iniciarSessao,
  encerrarSessao,
  enviarPergunta,
} from "../../services/chatService";
import sabiaperfil from "../../assets/sabiaperfil.png";
import "./Chat.css";
import ReactMarkdown from "react-markdown";
import {
  Plus,
  Trash2,
  User,
  Settings,
  LogOut,
  MessageSquare,
} from "lucide-react";

function iniciais(nome = "") {
  return nome
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0].toUpperCase())
    .join("");
}

function Recomendacoes({ lista }) {
  if (!lista || lista.length === 0) return null;
  return (
    <div className="recomendacoes">
      <p className="recomendacoes__titulo">Conteúdos recomendados</p>
      <div className="recomendacoes__lista">
        {lista.map((item, idx) => (
          <div key={idx} className="recomendacao-card">
            <span className="recomendacao-card__titulo">{item.titulo}</span>
            <span className="recomendacao-card__tipo">{item.tipo}</span>
            <a
              href={item.link}
              target="_blank"
              rel="noreferrer"
              className="recomendacao-card__link"
            >
              Acessar →
            </a>
          </div>
        ))}
      </div>
    </div>
  );
}

function Mensagem({ mensagem, nomeAluno }) {
  const eUsuario = mensagem.papel === "usuario";
  return (
    <div className={`mensagem ${eUsuario ? "usuario" : "assistente"}`}>
      {eUsuario ? (
        <div className="avatar-iniciais">{iniciais(nomeAluno)}</div>
      ) : (
        <img src={sabiaperfil} alt="SabiÁ" className="mensagem__avatar" />
      )}
      <div>
        <div className="mensagem__balao">
          {eUsuario ? (
            mensagem.conteudo
          ) : (
            <ReactMarkdown>{mensagem.conteudo}</ReactMarkdown>
          )}
        </div>
        {!eUsuario && mensagem.recomendacoes && (
          <Recomendacoes lista={mensagem.recomendacoes} />
        )}
      </div>
    </div>
  );
}

function MensagemCarregando() {
  return (
    <div className="mensagem assistente">
      <img src={sabiaperfil} alt="Sabiá" className="mensagem__avatar" />
      <div className="mensagem__balao">
        <div className="mensagem__loading">
          <span /><span /><span />
        </div>
      </div>
    </div>
  );
}

export default function Chat() {
  const { aluno, logout } = useAuth();
  const navegar = useNavigate();

  const [sessaoId, setSessaoId] = useState(null);
  const [mensagens, setMensagens] = useState([]);
  const [texto, setTexto] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [sessoes, setSessoes] = useState([]);

  const fimMensagensRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (aluno?.email) criarNovaSessao();
  }, []);

  useEffect(() => {
    fimMensagensRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [mensagens, carregando]);

  async function criarNovaSessao() {
    try {
      const dados = await iniciarSessao(aluno.email);
      setSessaoId(dados.sessao_id);
      setMensagens([
        {
          papel: "assistente",
          conteudo: `Olá, ${aluno.nome}! Sou o Sabiá, seu assistente de aprendizado. Como posso te ajudar hoje?`,
        },
      ]);
      setSessoes((ant) => [
        { id: dados.sessao_id, titulo: `Sessão ${ant.length + 1}` },
        ...ant,
      ]);
    } catch (erro) {
      console.error("Erro ao criar sessão:", erro);
    }
  }

  async function aoEnviar(evento) {
    evento.preventDefault();
    const pergunta = texto.trim();
    if (!pergunta || carregando || !sessaoId) return;

    setTexto("");
    setCarregando(true);

    setMensagens((ant) => [...ant, { papel: "usuario", conteudo: pergunta }]);

    try {
      const dados = await enviarPergunta(sessaoId, pergunta);
      setMensagens((ant) => [
        ...ant,
        {
          papel: "assistente",
          conteudo: dados.resposta,
          recomendacoes: dados.recomendacoes,
        },
      ]);
    } catch {
      setMensagens((ant) => [
        ...ant,
        {
          papel: "assistente",
          conteudo: "Desculpe, ocorreu um erro ao processar sua pergunta. Tente novamente.",
        },
      ]);
    } finally {
      setCarregando(false);
      inputRef.current?.focus();
    }
  }

  function aoTeclaPressionada(evento) {
    if (evento.key === "Enter" && !evento.shiftKey) {
      evento.preventDefault();
      aoEnviar(evento);
    }
  }

  async function aoSair() {
    if (sessaoId) {
      try { await encerrarSessao(sessaoId); } catch {}
    }
    logout();
    navegar("/entrar");
  }

  async function aoLimparChat() {
    if (sessaoId) {
      try { await encerrarSessao(sessaoId); } catch {}
    }
    criarNovaSessao();
  }

  return (
    <div className="tela-chat">

      {/* ── Sidebar ── */}
      <aside className="sidebar">
        <div className="sidebar__topo">
          <div className="sidebar__logo">
          </div>

          <button className="btn-novo-chat" onClick={criarNovaSessao}>
            <Plus size={16} color="#2563eb" />
            <span>Novo chat</span>
          </button>
        </div>

        <nav className="sidebar__sessoes">
          {sessoes.map((s) => (
            <button
              key={s.id}
              className={`sidebar__sessao-item ${s.id === sessaoId ? "ativo" : ""}`}
              onClick={() => setSessaoId(s.id)}
            >
              <MessageSquare size={15} color="#2563eb" />
              <span>{s.titulo}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar__rodape">
          <button className="sidebar__link" onClick={aoLimparChat}>
            <Trash2 size={16} color="#2563eb" />
            <span>Limpar chat</span>
          </button>
          <button className="sidebar__link" onClick={() => navegar("/perfil")}>
            <User size={16} color="#2563eb" />
            <span>Minha conta</span>
          </button>
          <button className="sidebar__link" onClick={() => navegar("/configuracoes")}>
            <Settings size={16} color="#2563eb" />
            <span>Configurações</span>
          </button>
          <button className="sidebar__link sair" onClick={aoSair}>
            <LogOut size={16} color="#dc2626" />
            <span>Sair</span>
          </button>
        </div>
      </aside>

      {/* ── Área principal ── */}
      <main className="chat-principal">
        <header className="chat-header">
          <div className="chat-header__info">
            <img src={sabiaperfil} alt="Sabiá" className="chat-header__avatar" />
            <div>
              <p className="chat-header__nome">Sabiá</p>
              <p className="chat-header__subtitulo">Apoio ao aprendizado de algoritmos de busca</p>
            </div>
          </div>
          <div className="chat-header__aluno">
            <div className="avatar-iniciais">{iniciais(aluno?.nome)}</div>
            <span>{aluno?.nome}</span>
          </div>
        </header>

        <div className="chat-mensagens">
          {mensagens.map((msg, idx) => (
            <Mensagem key={idx} mensagem={msg} nomeAluno={aluno?.nome} />
          ))}
          {carregando && <MensagemCarregando />}
          <div ref={fimMensagensRef} />
        </div>

        <div className="chat-input-area">
          <form className="chat-input-form" onSubmit={aoEnviar}>
            <textarea
              ref={inputRef}
              className="chat-input"
              placeholder="Escreva sua mensagem..."
              value={texto}
              onChange={(e) => setTexto(e.target.value)}
              onKeyDown={aoTeclaPressionada}
              rows={1}
              disabled={carregando}
            />
            <button
              type="submit"
              className="btn-enviar"
              disabled={!texto.trim() || carregando}
            >
              <Plus size={18} color="#fff" style={{ transform: "rotate(45deg)" }} />
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}
