// Lista de vídeos (composições) do projeto. Aqui ficam tamanho, quadros por segundo e duração.
import { Composition } from "remotion";
import { Abertura } from "./Abertura";

export const Root = () => (
  <Composition
    id="Abertura"
    component={Abertura}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={150} // 5 s x 30 qps
  />
);
