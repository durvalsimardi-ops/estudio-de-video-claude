// A mesma abertura do exemplo do HyperFrames, escrita em React para o Remotion.
// A ideia é igual: o Remotion diz o número do quadro, e o componente desenha aquele quadro.
import { Fragment } from "react";
import { AbsoluteFill, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { loadFont } from "@remotion/fonts";

// ===== FONTES (OFL): o Remotion espera carregar antes de gravar o primeiro quadro =====
loadFont({ family: "Fraunces", url: staticFile("fontes/Fraunces-600.woff2"), weight: "600" });
loadFont({ family: "Inter", url: staticFile("fontes/Inter-400.woff2"), weight: "400" });

// ===== O QUE O ALUNO MAIS TROCA =====
const TITULO = "Seu café já está passando.";
const APOIO = "Café bem feito, sem pressa.";
const COR = { azul: "#2E6BFF", creme: "#F7F3EC", cafe: "#2B211B", branco: "#FFFFFF" };

// ===== FERRAMENTAS DE TEMPO (as mesmas do exemplo HyperFrames) =====
const prende = (x: number, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const prog = (t: number, ini: number, fim: number) => prende((t - ini) / (fim - ini));
const freia = (x: number) => 1 - Math.pow(1 - x, 4);
const suave = (x: number) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
const mola = (x: number) => (x <= 0 ? 0 : x >= 1 ? 1 : 1 - Math.exp(-6 * x) * Math.cos(8 * x));

const luz: React.CSSProperties = {
  position: "absolute", width: 1400, height: 1400, borderRadius: "50%",
  background: "radial-gradient(circle, rgba(255,255,255,.20) 0%, rgba(255,255,255,0) 62%)",
};

export const Abertura = () => {
  const quadro = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = quadro / fps; // segundo atual

  const qsai = suave(prog(t, 2.55, 2.95)); // a primeira parte sobe e some
  const sobe = -80 * qsai;
  const qa = freia(prog(t, 0.85, 1.3)); // frase de apoio
  const qs = suave(prog(t, 2.55, 3.1)); // sol creme
  const ql = freia(prog(t, 2.85, 3.3)); // logo

  return (
    <AbsoluteFill style={{ background: COR.azul, overflow: "hidden" }}>
      {/* fundo: duas luzes que passeiam devagar */}
      <div style={{ ...luz, transform: `translate(${-300 + Math.sin(t * 0.8) * 90}px, ${-200 + Math.cos(t * 0.6) * 70}px)` }} />
      <div style={{ ...luz, transform: `translate(${100 + Math.cos(t * 0.7) * 80}px, ${900 + Math.sin(t * 0.9) * 90}px)` }} />

      {/* xícara em traço, na tela desde o quadro 0; o vapor anda com o tempo */}
      <svg viewBox="0 0 200 200" fill="none" stroke="#fff" strokeWidth={7} strokeLinecap="round" strokeLinejoin="round"
        style={{ position: "absolute", left: 300, top: 300, width: 480, height: 480, opacity: 1 - qsai,
          transform: `translateY(${-20 * suave(prog(t, 0, 2.95)) + sobe}px)` }}>
        <path d="M40 92 h104 v28 a42 42 0 0 1 -42 42 h-20 a42 42 0 0 1 -42 -42 z" />
        <path d="M144 102 h10 a18 18 0 0 1 0 36 h-12" />
        <path d="M26 178 h148" />
        {[70, 94, 118].map((x, i) => (
          <path key={x} d={`M${x} 74 c-10 -12 10 -20 0 -34 c-8 -10 4 -18 0 -26`} pathLength={100}
            strokeDasharray="40 60" strokeDashoffset={-(t * 45 + i * 33)} />
        ))}
      </svg>

      {/* título palavra a palavra */}
      <div style={{ position: "absolute", left: 90, right: 90, top: 860, textAlign: "center", color: COR.branco,
        font: '600 150px/1.04 "Fraunces", serif', letterSpacing: "-0.01em" }}>
        {TITULO.split(" ").map((p, i) => {
          const ini = 0.25 + i * 0.15;
          const q = prog(t, ini, ini + 0.7);
          // o espaço fica fora do <span>, senão some e as palavras grudam
          return (
            <Fragment key={i}>
            <span style={{ display: "inline-block", margin: "0 .03em",
              opacity: freia(prog(t, ini, ini + 0.3)) * (1 - qsai),
              transform: `translateY(${(1 - mola(q)) * 90 + sobe}px) rotate(${(1 - freia(q)) * 4}deg)` }}>
              {p}
            </span>{" "}
            </Fragment>
          );
        })}
      </div>

      {/* frase de apoio */}
      <div style={{ position: "absolute", left: 0, right: 0, top: 1400, textAlign: "center", color: COR.branco,
        font: '400 52px/1.3 "Inter", sans-serif', opacity: qa * (1 - qsai), transform: `translateY(${(1 - qa) * 30 + sobe}px)` }}>
        {APOIO}
      </div>

      {/* sol creme que nasce de baixo */}
      <AbsoluteFill style={{ background: COR.creme, clipPath: `circle(${qs * 2200}px at 540px 2050px)` }} />

      {/* logo do Café Aurora (copiado de marcas/cafe-aurora/logo.svg) */}
      <div style={{ position: "absolute", left: 0, right: 0, top: 860, display: "flex", justifyContent: "center",
        opacity: ql, transform: `scale(${0.92 + 0.08 * ql})` }}>
        <svg viewBox="0 0 440 120" style={{ width: 760, overflow: "visible" }}>
          <g fill="none" stroke={COR.azul} strokeWidth={6} strokeLinecap="round">
            <path d="M22 70 h68 v10 a22 22 0 0 1 -22 22 h-24 a22 22 0 0 1 -22 -22 z" fill={COR.azul} />
            <path d="M90 74 h8 a10 10 0 0 1 0 20 h-8" />
            <path d="M36 58 a20 20 0 0 1 40 0" />
            <path d="M56 26 v10 M30 38 l7 7 M82 38 l-7 7" opacity={0.3 + 0.7 * suave(prog(t, 3.3, 3.7))} />
          </g>
          <text x={122} y={84} fontFamily="Fraunces, serif" fontWeight={600} fontSize={52} fill={COR.cafe}>Café Aurora</text>
        </svg>
      </div>
    </AbsoluteFill>
  );
};
