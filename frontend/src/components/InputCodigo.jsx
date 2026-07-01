// 6 caixinhas de 1 dígito, com avanço automático e suporte a colar o código inteiro
import { useRef, useState } from "react";
import "./InputCodigo.css";

const QUANTIDADE_DIGITOS = 6;

export default function InputCodigo({ onChange }) {
  const [digitos, setDigitos] = useState(Array(QUANTIDADE_DIGITOS).fill(""));
  const inputsRef = useRef([]);

  function atualizarDigito(indice, valor) {
    const valorLimpo = valor.replace(/[^0-9]/g, "").slice(-1);
    const novosDigitos = [...digitos];
    novosDigitos[indice] = valorLimpo;
    setDigitos(novosDigitos);
    onChange(novosDigitos.join(""));

    if (valorLimpo && indice < QUANTIDADE_DIGITOS - 1) {
      inputsRef.current[indice + 1]?.focus();
    }
  }

  function aoApagar(indice, evento) {
    if (evento.key === "Backspace" && !digitos[indice] && indice > 0) {
      inputsRef.current[indice - 1]?.focus();
    }
  }

  function aoColar(evento) {
    const colado = evento.clipboardData.getData("text").replace(/[^0-9]/g, "");
    if (!colado) return;
    evento.preventDefault();
    const novosDigitos = colado.slice(0, QUANTIDADE_DIGITOS).split("");
    while (novosDigitos.length < QUANTIDADE_DIGITOS) novosDigitos.push("");
    setDigitos(novosDigitos);
    onChange(novosDigitos.join(""));
    const ultimoPreenchido = Math.min(colado.length, QUANTIDADE_DIGITOS) - 1;
    inputsRef.current[Math.max(ultimoPreenchido, 0)]?.focus();
  }

  return (
    <div className="input-codigo" onPaste={aoColar}>
      {digitos.map((digito, indice) => (
        <input
          key={indice}
          ref={(el) => (inputsRef.current[indice] = el)}
          type="text"
          inputMode="numeric"
          maxLength={1}
          value={digito}
          onChange={(e) => atualizarDigito(indice, e.target.value)}
          onKeyDown={(e) => aoApagar(indice, e)}
        />
      ))}
    </div>
  );
}
