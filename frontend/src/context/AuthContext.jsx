import { createContext, useContext, useState, useEffect } from "react";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [aluno, setAluno] = useState(() => {
    const salvo = localStorage.getItem("sabia_aluno");
    return salvo ? JSON.parse(salvo) : null;
  });

  useEffect(() => {
    if (aluno) {
      localStorage.setItem("sabia_aluno", JSON.stringify(aluno));
    } else {
      localStorage.removeItem("sabia_aluno");
    }
  }, [aluno]);

  function login(dadosAluno) { setAluno(dadosAluno); }
  function logout() { setAluno(null); }

  return (
    <AuthContext.Provider value={{ aluno, login, logout, estaLogado: !!aluno }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const contexto = useContext(AuthContext);
  if (!contexto) throw new Error("useAuth precisa ser usado dentro de um AuthProvider");
  return contexto;
}
