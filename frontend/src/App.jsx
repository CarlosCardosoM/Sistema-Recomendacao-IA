import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";

import Entrar from "./pages/Auth/Entrar";
import VerificarLogin from "./pages/Auth/VerificarLogin";
import CriarConta from "./pages/Auth/CriarConta";
import VerificarCadastro from "./pages/Auth/VerificarCadastro";

import "./styles/global.css";

function RotaPrivada({ children }) {
  const { estaLogado } = useAuth();
  return estaLogado ? children : <Navigate to="/entrar" replace />;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Navigate to="/entrar" replace />} />
          <Route path="/entrar" element={<Entrar />} />
          <Route path="/verificar-login" element={<VerificarLogin />} />
          <Route path="/cadastro" element={<CriarConta />} />
          <Route path="/verificar-cadastro" element={<VerificarCadastro />} />

          <Route
            path="/chat"
            element={
              <RotaPrivada>
                <div style={{ padding: 40 }}>Tela de chat — próxima etapa</div>
              </RotaPrivada>
            }
          />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
