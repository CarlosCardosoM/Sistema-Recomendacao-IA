// Mostra "Expira em MM:SS" e chama onExpirar() quando zera.
// Token do backend expira em 10 min (ver token_expira_em no aluno_controller.py)
import { useEffect, useState } from "react";

const DEZ_MINUTOS_EM_SEGUNDOS = 10 * 60;

export default function ContadorExpiracao({ onExpirar, reiniciarChave }) {
  const [segundosRestantes, setSegundosRestantes] = useState(DEZ_MINUTOS_EM_SEGUNDOS);

  useEffect(() => {
    setSegundosRestantes(DEZ_MINUTOS_EM_SEGUNDOS);
  }, [reiniciarChave]);

  useEffect(() => {
    if (segundosRestantes <= 0) {
      onExpirar?.();
      return;
    }
    const intervalo = setInterval(() => {
      setSegundosRestantes((atual) => atual - 1);
    }, 1000);
    return () => clearInterval(intervalo);
  }, [segundosRestantes, onExpirar]);

  const minutos = String(Math.floor(segundosRestantes / 60)).padStart(2, "0");
  const segundos = String(segundosRestantes % 60).padStart(2, "0");

  return (
    <p style={{ fontSize: 12, color: "var(--cor-texto-terciario)", marginBottom: 20 }}>
      {segundosRestantes > 0 ? `Expira em ${minutos}:${segundos}` : "Código expirado — solicite um novo"}
    </p>
  );
}
