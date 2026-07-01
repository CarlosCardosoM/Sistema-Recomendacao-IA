import imagemLateral from "../assets/sabialateral.png";
import "./PainelLateral.css";

export default function PainelLateral({ titulo, texto }) {
  return (
    <div
      className="painel-lateral"
      style={{
        backgroundImage: `url(${imagemLateral})`,
      }}
    >
      <div className="painel-lateral__overlay">

        <div className="painel-lateral__topo">
          <div>
          </div>
        </div>

        <div className="painel-lateral__meio">
          <h1>{titulo}</h1>
          <p>{texto}</p>
        </div>

        <p className="painel-lateral__rodape">
          © 2026 Sabiá.
        </p>

      </div>
    </div>
  );
}