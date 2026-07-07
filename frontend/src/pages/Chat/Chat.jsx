import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import {
  iniciarSessao,
  encerrarSessao,
  excluirSessao,
  enviarPergunta,
  buscarHistorico,
  abrirConteudo,
  fecharConteudo,
} from "../../services/chatService";
import sabiaperfil from "../../assets/sabiaperfil.png";
import "./Chat.css";
import ReactMarkdown from "react-markdown";
import { Plus, Trash2, User, LogOut, Send, Pencil, Check } from "lucide-react";

// Chaves isoladas por e-mail — cada conta tem sua própria lista de sessões
// no localStorage, para trocar de conta no mesmo navegador não misturar
// o histórico de uma pessoa com o de outra
function chaveSessoes(email) {
  return `sabia_sessoes_${email}`;
}

function chaveContador(email) {
  return `sabia_contador_sessoes_${email}`;
}

function iniciais(nome = "") {
  return nome.split(" ").filter(Boolean).slice(0, 2).map((p) => p[0].toUpperCase()).join("");
}

// ── Contador de sessões criadas por conta ──
// Persiste no localStorage para nunca repetir o número
// mesmo após limpar a lista de sessões
function proximoNumeroSessao(chave) {
  const atual = parseInt(localStorage.getItem(chave) || "0", 10);
  const proximo = atual + 1;
  localStorage.setItem(chave, String(proximo));
  return proximo;
}

function CardRecomendacao({ item, aluno }) {
  const [acessado, setAcessado] = useState(false);

  async function aoAcessar() {
    if (acessado) return;
    try {
      const dados = await abrirConteudo(aluno.email, item.conteudo_id);
      setAcessado(true);
      window.open(item.link, "_blank", "noreferrer");
      setTimeout(async () => {
        try { await fecharConteudo(dados.interacao_id); } catch {}
      }, 30000);
    } catch {
      window.open(item.link, "_blank", "noreferrer");
    }
  }

  return (
    <div className={`recomendacao-card ${acessado ? "acessado" : ""}`}>
      <span className="recomendacao-card__titulo">{item.titulo}</span>
      <span className="recomendacao-card__tipo">{item.tipo}</span>
      <button className="recomendacao-card__link" onClick={aoAcessar}>
        {acessado ? "✓ Acessado" : "Acessar →"}
      </button>
    </div>
  );
}

function Recomendacoes({ lista, aluno }) {
  if (!lista || lista.length === 0) return null;
  return (
    <div className="recomendacoes">
      <p className="recomendacoes__titulo">Conteúdos recomendados</p>
      <div className="recomendacoes__lista">
        {lista.map((item, idx) => (
          <CardRecomendacao key={idx} item={item} aluno={aluno} />
        ))}
      </div>
    </div>
  );
}

function Mensagem({ mensagem, nomeAluno, aluno }) {
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
          {eUsuario ? mensagem.conteudo : <ReactMarkdown>{mensagem.conteudo}</ReactMarkdown>}
        </div>
        {!eUsuario && mensagem.recomendacoes && mensagem.recomendacoes.length > 0 && (
          <Recomendacoes lista={mensagem.recomendacoes} aluno={aluno} />
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
        <div className="mensagem__loading"><span /><span /><span /></div>
      </div>
    </div>
  );
}

function IconeChat({ size = 16, color = "#2563eb" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}

function ItemSessao({ sessao, ativo, aoClicar, aoRenomear, aoExcluir }) {
  const [editando, setEditando] = useState(false);
  const [novoNome, setNovoNome] = useState(sessao.titulo);
  const inputRef = useRef(null);

  useEffect(() => {
    if (editando) inputRef.current?.focus();
  }, [editando]);

  function aoClicarEditar(evento) {
    evento.stopPropagation();
    setNovoNome(sessao.titulo);
    setEditando(true);
  }

  function aoConfirmar() {
    aoRenomear(sessao.id, novoNome.trim() || sessao.titulo);
    setEditando(false);
  }

  function aoTecla(evento) {
    if (evento.key === "Enter") aoConfirmar();
    if (evento.key === "Escape") { setNovoNome(sessao.titulo); setEditando(false); }
  }

  if (editando) {
    return (
      <div className="sidebar__sessao-item ativo sidebar__sessao-editando">
        <IconeChat size={15} color="#2563eb" />
        <input ref={inputRef} className="sidebar__sessao-input" value={novoNome}
          onChange={(e) => setNovoNome(e.target.value)} onKeyDown={aoTecla}
          onBlur={aoConfirmar} maxLength={30} />
        <button className="sidebar__sessao-confirmar" onClick={aoConfirmar}>
          <Check size={13} color="#2563eb" />
        </button>
      </div>
    );
  }

  return (
    <button className={`sidebar__sessao-item ${ativo ? "ativo" : ""}`} onClick={aoClicar}>
      <IconeChat size={15} color={ativo ? "#2563eb" : "#6b7280"} />
      <span className="sidebar__sessao-titulo">{sessao.titulo}</span>
      <div className="sidebar__sessao-acoes">
        <button className="sidebar__sessao-editar" onClick={aoClicarEditar} title="Renomear">
          <Pencil size={12} color="#9ca3af" />
        </button>
        <button
          className="sidebar__sessao-excluir"
          onClick={(e) => { e.stopPropagation(); aoExcluir(sessao.id); }}
          title="Excluir sessão"
        >
          <Trash2 size={12} color="#9ca3af" />
        </button>
      </div>
    </button>
  );
}

export default function Chat() {
  const { aluno, logout } = useAuth();
  const navegar = useNavigate();

  const chaveSessoesAtual  = chaveSessoes(aluno?.email);
  const chaveContadorAtual = chaveContador(aluno?.email);

  const [sessoes, setSessoes] = useState(() => {
    try {
      const salvas = localStorage.getItem(chaveSessoesAtual);
      return salvas ? JSON.parse(salvas) : [];
    } catch { return []; }
  });

  const [sessaoId, setSessaoId] = useState(null);
  const [mensagens, setMensagens] = useState([]);
  const [carregandoHistorico, setCarregandoHistorico] = useState(false);
  const [texto, setTexto] = useState("");
  const [carregando, setCarregando] = useState(false);

  const fimMensagensRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    try { localStorage.setItem(chaveSessoesAtual, JSON.stringify(sessoes)); } catch {}
  }, [sessoes, chaveSessoesAtual]);

  useEffect(() => {
    if (!aluno?.email) return;
    if (sessoes.length > 0) {
      carregarSessao(sessoes[0].id);
    } else {
      criarNovaSessao();
    }
  }, []);

  useEffect(() => {
    fimMensagensRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [mensagens, carregando]);

  async function carregarSessao(id) {
    setSessaoId(id);
    setCarregandoHistorico(true);
    try {
      const historico = await buscarHistorico(id, aluno.email);
      if (historico.length === 0) {
        setMensagens([{
          papel: "assistente",
          conteudo: `Olá, ${aluno.nome}! Sou o Sabiá, seu assistente de aprendizado. Como posso te ajudar hoje?`,
        }]);
      } else {
        setMensagens(historico.map((m) => ({
          papel:         m.papel,
          conteudo:      m.conteudo,
          recomendacoes: m.recomendacoes || [],
        })));
      }
    } catch (erro) {
      if (erro?.response?.status === 404) {
        // Sessão de fato não existe mais no banco — remove só ela e recomeça
        const novaLista = sessoes.filter((s) => s.id !== id);
        setSessoes(novaLista);
        if (novaLista.length > 0) {
          carregarSessao(novaLista[0].id);
        } else {
          criarNovaSessao();
        }
      } else {
        // Falha de rede/backend indisponível — não apaga o histórico local,
        // apenas avisa e mantém a lista de sessões intacta
        console.error("Erro ao carregar histórico:", erro);
        setMensagens([{
          papel: "assistente",
          conteudo: "Não foi possível carregar esta conversa. Verifique se o servidor está rodando e tente novamente.",
        }]);
      }
    } finally {
      setCarregandoHistorico(false);
    }
  }

  async function criarNovaSessao() {
    try {
      const dados = await iniciarSessao(aluno.email);
      // Usa contador por conta para nunca repetir o número da sessão
      const numero = proximoNumeroSessao(chaveContadorAtual);
      const novaSessao = { id: dados.sessao_id, titulo: `Sessão ${numero}` };
      setSessaoId(dados.sessao_id);
      setMensagens([{
        papel: "assistente",
        conteudo: `Olá, ${aluno.nome}! Sou o Sabiá, seu assistente de aprendizado. Como posso te ajudar hoje?`,
      }]);
      setSessoes((ant) => [novaSessao, ...ant]);
    } catch (erro) {
      console.error("Erro ao criar sessão:", erro);
    }
  }

  function aoRenomearSessao(id, novoTitulo) {
    setSessoes((ant) => ant.map((s) => (s.id === id ? { ...s, titulo: novoTitulo } : s)));
  }

  async function aoExcluirSessao(id) {
    try { await excluirSessao(id, aluno.email); } catch {}
    const novaLista = sessoes.filter((s) => s.id !== id);
    setSessoes(novaLista);
    if (id === sessaoId) {
      if (novaLista.length > 0) {
        carregarSessao(novaLista[0].id);
      } else {
        criarNovaSessao();
      }
    }
  }

  async function aoLimparChat() {
    if (sessaoId) await aoExcluirSessao(sessaoId);
    else criarNovaSessao();
  }

  async function aoEnviar(evento) {
    evento.preventDefault();
    const pergunta = texto.trim();
    if (!pergunta || carregando || !sessaoId) return;

    setTexto("");
    setCarregando(true);
    setMensagens((ant) => [...ant, { papel: "usuario", conteudo: pergunta }]);

    try {
      const dados = await enviarPergunta(sessaoId, pergunta, aluno.email);
      setMensagens((ant) => [
        ...ant,
        {
          papel:         "assistente",
          conteudo:      dados.resposta,
          // Usa recomendacoes da resposta em tempo real
          // São mais completas que o histórico (inclui recomendacao_service)
          recomendacoes: dados.recomendacoes || [],
        },
      ]);
    } catch {
      setMensagens((ant) => [
        ...ant,
        { papel: "assistente", conteudo: "Desculpe, ocorreu um erro. Tente novamente." },
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
    if (sessaoId) { try { await encerrarSessao(sessaoId, aluno.email); } catch {} }
    logout();
    navegar("/entrar");
  }

  return (
    <div className="tela-chat">
      <aside className="sidebar">
        <div className="sidebar__topo">
          <button className="btn-novo-chat" onClick={criarNovaSessao}>
            <span className="btn-novo-chat__icone"><Plus size={17} strokeWidth={2.5} /></span>
            <span>Novo chat</span>
          </button>
        </div>

        <nav className="sidebar__sessoes">
          {sessoes.map((s) => (
            <ItemSessao
              key={s.id}
              sessao={s}
              ativo={s.id === sessaoId}
              aoClicar={() => carregarSessao(s.id)}
              aoRenomear={aoRenomearSessao}
              aoExcluir={aoExcluirSessao}
            />
          ))}
        </nav>

        <div className="sidebar__rodape">
          <button className="sidebar__link" onClick={aoLimparChat}>
            <Trash2 size={16} strokeWidth={1.8} /><span>Limpar chat</span>
          </button>
          <button className="sidebar__link" onClick={() => navegar("/perfil")}>
            <User size={16} strokeWidth={1.8} /><span>Minha conta</span>
          </button>
          <button className="sidebar__link sair" onClick={aoSair}>
            <LogOut size={16} strokeWidth={1.8} /><span>Sair</span>
          </button>
        </div>
      </aside>

      <main className="chat-principal">
        <header className="chat-header">
          <div className="chat-header__info">
            <img src={sabiaperfil} alt="Sabiá" className="chat-header__avatar" />
            <div>
              <p className="chat-header__nome">SabiÁ</p>
              <p className="chat-header__subtitulo">Apoio ao aprendizado de algoritmos de busca</p>
            </div>
          </div>
          <div className="chat-header__aluno">
            <div className="avatar-iniciais">{iniciais(aluno?.nome)}</div>
            <span>{aluno?.nome}</span>
          </div>
        </header>

        <div className="chat-mensagens">
          {carregandoHistorico ? (
            <div className="chat-carregando-historico">Carregando conversa...</div>
          ) : (
            mensagens.map((msg, idx) => (
              <Mensagem key={idx} mensagem={msg} nomeAluno={aluno?.nome} aluno={aluno} />
            ))
          )}
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
              disabled={carregando || carregandoHistorico}
            />
            <button type="submit" className="btn-enviar" disabled={!texto.trim() || carregando}>
              <Send size={16} strokeWidth={2} color="#fff" />
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}
