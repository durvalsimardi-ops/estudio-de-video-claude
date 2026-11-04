// Recorte de pessoa e posição do rosto, com o Vision do macOS (só funciona no Mac).
//
// Uso:
//   bash ferramentas/recorte.sh <video> <pasta-de-saida> [opções]
//   (ou direto, mais lento para começar: swift ferramentas/recorte.swift <video> <pasta> [opções])
//
// Opções:
//   --so-rostos            não grava o matte; só o rostos.json (bem mais rápido)
//   --inicio 12.5          começa neste segundo do vídeo
//   --fim 25               termina neste segundo
//   --fps 30               quadros por segundo da análise (padrão 30; 5 basta para conferir gravação)
//   --qualidade precisa    precisa | equilibrada | rapida (padrão: precisa com matte, equilibrada sem)
//
// Saída na pasta:
//   matte.mp4    vídeo em preto e branco: branco = pessoa, preto = fundo (mesmo tamanho do vídeo)
//   rostos.json  por quadro: tempo, caixa do rosto e topo da cabeça (cabelo incluso), em pixels

import AVFoundation
import CoreImage
import CoreVideo
import Foundation
import Vision

// ---------- argumentos ----------
func sair(_ texto: String) -> Never {
    FileHandle.standardError.write((texto + "\n").data(using: .utf8)!)
    exit(1)
}

var args = Array(CommandLine.arguments.dropFirst())
func opcao(_ nome: String) -> String? {
    guard let i = args.firstIndex(of: nome), i + 1 < args.count else { return nil }
    let v = args[i + 1]
    args.removeSubrange(i...(i + 1))
    return v
}
func chave(_ nome: String) -> Bool {
    guard let i = args.firstIndex(of: nome) else { return false }
    args.remove(at: i)
    return true
}

let soRostos = chave("--so-rostos")
let inicio = Double(opcao("--inicio") ?? "0") ?? 0
let fimPedido = Double(opcao("--fim") ?? "") ?? Double.infinity
let fps = Double(opcao("--fps") ?? "30") ?? 30
let qualidadeTexto = opcao("--qualidade") ?? (soRostos ? "equilibrada" : "precisa")
if args.count < 2 {
    sair("Uso: bash ferramentas/recorte.sh <video> <pasta-de-saida> [--so-rostos] [--inicio s] [--fim s] [--fps 30] [--qualidade precisa|equilibrada|rapida]")
}
let entrada = URL(fileURLWithPath: args[0])
let pasta = URL(fileURLWithPath: args[1], isDirectory: true)
try? FileManager.default.createDirectory(at: pasta, withIntermediateDirectories: true)
let arquivoMatte = pasta.appendingPathComponent("matte.mp4")
let arquivoRostos = pasta.appendingPathComponent("rostos.json")

// ---------- vídeo de entrada ----------
let asset = AVURLAsset(url: entrada)
guard let trilha = try await asset.loadTracks(withMediaType: .video).first else { sair("Não achei imagem em \(entrada.path)") }
let (tamanhoNatural, transformacao) = try await trilha.load(.naturalSize, .preferredTransform)
let duracao = try await asset.load(.duration).seconds
let fim = min(fimPedido, duracao)

// Vídeo gravado em pé no celular pode vir "deitado" com uma marca de rotação. Endireita igual ao ffmpeg.
func orientacao(_ t: CGAffineTransform) -> CGImagePropertyOrientation {
    if t.a == 0 && t.b == 1 && t.c == -1 && t.d == 0 { return .right }
    if t.a == 0 && t.b == -1 && t.c == 1 && t.d == 0 { return .left }
    if t.a == -1 && t.d == -1 { return .down }
    return .up
}
let giro = orientacao(transformacao)
let deitado = (giro == .right || giro == .left)
let W = Int(deitado ? tamanhoNatural.height : tamanhoNatural.width) & ~1
let H = Int(deitado ? tamanhoNatural.width : tamanhoNatural.height) & ~1

let leitor = try AVAssetReader(asset: asset)
let saidaLeitor = AVAssetReaderTrackOutput(track: trilha, outputSettings: [
    kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA,
])
saidaLeitor.alwaysCopiesSampleData = false
leitor.timeRange = CMTimeRange(start: CMTime(seconds: inicio, preferredTimescale: 600),
                               end: CMTime(seconds: fim, preferredTimescale: 600))
leitor.add(saidaLeitor)
leitor.startReading()

// ---------- matte de saída (só se pedido) ----------
var gravador: AVAssetWriter? = nil
var entradaGravador: AVAssetWriterInput? = nil
var adaptador: AVAssetWriterInputPixelBufferAdaptor? = nil
if !soRostos {
    try? FileManager.default.removeItem(at: arquivoMatte)
    let g = try AVAssetWriter(outputURL: arquivoMatte, fileType: .mp4)
    let e = AVAssetWriterInput(mediaType: .video, outputSettings: [
        AVVideoCodecKey: AVVideoCodecType.h264, AVVideoWidthKey: W, AVVideoHeightKey: H,
        AVVideoCompressionPropertiesKey: [AVVideoAverageBitRateKey: 14_000_000],
    ])
    let a = AVAssetWriterInputPixelBufferAdaptor(assetWriterInput: e, sourcePixelBufferAttributes: [
        kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA,
        kCVPixelBufferWidthKey as String: W, kCVPixelBufferHeightKey as String: H,
    ])
    g.add(e)
    g.startWriting()
    g.startSession(atSourceTime: .zero)
    gravador = g; entradaGravador = e; adaptador = a
}

// ---------- pedidos ao Vision ----------
let contexto = CIContext(options: [.useSoftwareRenderer: false])
let recorte = VNGeneratePersonSegmentationRequest()
recorte.qualityLevel = qualidadeTexto == "rapida" ? .fast : (qualidadeTexto == "equilibrada" ? .balanced : .accurate)
recorte.outputPixelFormat = kCVPixelFormatType_OneComponent8
let pedidoRosto = VNDetectFaceRectanglesRequest()

// Topo da cabeça: sobe a partir do alto do rosto, numa faixa da largura do rosto,
// e para na última linha com pessoa antes de um vão. Assim o cabelo entra e a mão levantada ao lado não.
func topoDaCabeca(_ mascara: CVPixelBuffer, rosto: CGRect?) -> (topo: Double, cortada: Bool)? {
    CVPixelBufferLockBaseAddress(mascara, .readOnly)
    defer { CVPixelBufferUnlockBaseAddress(mascara, .readOnly) }
    let mw = CVPixelBufferGetWidth(mascara), mh = CVPixelBufferGetHeight(mascara)
    let passo = CVPixelBufferGetBytesPerRow(mascara)
    guard let base = CVPixelBufferGetBaseAddress(mascara)?.assumingMemoryBound(to: UInt8.self) else { return nil }
    func fracao(_ linha: Int, _ x0: Int, _ x1: Int) -> Double {
        var n = 0
        let p = base + linha * passo
        for x in x0..<x1 where p[x] > 127 { n += 1 }
        return Double(n) / Double(max(1, x1 - x0))
    }
    if let r = rosto {
        // r está normalizado com origem embaixo; a máscara tem a linha 0 em cima
        let x0 = max(0, Int((r.midX - r.width * 0.35) * Double(mw)))
        let x1 = min(mw, max(x0 + 1, Int((r.midX + r.width * 0.35) * Double(mw))))
        let partida = min(mh - 1, max(0, Int((1 - r.midY) * Double(mh))))
        let vaoMaximo = max(2, mh / 40)
        var ultima = -1, vao = 0
        var linha = partida
        while linha >= 0 {
            if fracao(linha, x0, x1) >= 0.25 { ultima = linha; vao = 0 } else {
                vao += 1
                if vao > vaoMaximo && ultima >= 0 { break }
            }
            linha -= 1
        }
        if ultima < 0 { return nil }
        return (Double(ultima) / Double(mh), ultima == 0)
    }
    // sem rosto: usa a linha mais alta com um pouco de pessoa
    for linha in 0..<mh where fracao(linha, 0, mw) >= 0.02 {
        return (Double(linha) / Double(mh), linha == 0)
    }
    return nil
}

func arred(_ v: Double) -> Double { (v * 10).rounded() / 10 }

var quadros: [[String: Any]] = []
var proximo = inicio
var indice: Int64 = 0
var mascaraAnterior: CIImage? = nil
let area = CGRect(x: 0, y: 0, width: W, height: H)

while let amostra = saidaLeitor.copyNextSampleBuffer() {
    let t = CMSampleBufferGetPresentationTimeStamp(amostra).seconds
    guard t + 1e-6 >= proximo, let pb = CMSampleBufferGetImageBuffer(amostra) else { continue }
    while proximo <= t + 1e-6 { proximo += 1.0 / fps }

    var imagem = CIImage(cvPixelBuffer: pb).oriented(giro)
    imagem = imagem.transformed(by: CGAffineTransform(translationX: -imagem.extent.minX, y: -imagem.extent.minY))
    let manejador = VNImageRequestHandler(ciImage: imagem, options: [:])
    try? manejador.perform([recorte, pedidoRosto])

    let rosto = pedidoRosto.results?.max(by: { $0.boundingBox.width < $1.boundingBox.width })?.boundingBox
    let mascaraVision = recorte.results?.first?.pixelBuffer

    var q: [String: Any] = ["t": (t * 1000).rounded() / 1000]
    if let r = rosto {
        q["rosto"] = ["x": arred(r.minX * Double(W)), "y": arred((1 - r.maxY) * Double(H)),
                      "w": arred(r.width * Double(W)), "h": arred(r.height * Double(H))]
    } else { q["rosto"] = NSNull() }
    if let m = mascaraVision, let topo = topoDaCabeca(m, rosto: rosto) {
        q["topo_cabeca"] = arred(topo.topo * Double(H))
        q["cabeca_cortada"] = topo.cortada
    } else { q["topo_cabeca"] = NSNull(); q["cabeca_cortada"] = false }
    quadros.append(q)

    if let a = adaptador, let e = entradaGravador {
        var mascara: CIImage
        if let m = mascaraVision {
            let mi = CIImage(cvPixelBuffer: m)
            mascara = mi.transformed(by: CGAffineTransform(scaleX: CGFloat(W) / mi.extent.width, y: CGFloat(H) / mi.extent.height))
            // borda levemente suave e mistura com o quadro anterior: o recorte treme menos
            mascara = mascara.applyingFilter("CIGaussianBlur", parameters: ["inputRadius": 1.2]).cropped(to: area)
            if let anterior = mascaraAnterior {
                mascara = mascara.applyingFilter("CIDissolveTransition", parameters: ["inputTargetImage": anterior, "inputTime": 0.2])
            }
        } else {
            mascara = mascaraAnterior ?? CIImage(color: .black).cropped(to: area)
        }
        var buffer: CVPixelBuffer?
        CVPixelBufferPoolCreatePixelBuffer(nil, a.pixelBufferPool!, &buffer)
        guard let saida = buffer else { sair("Sem memória para o quadro \(indice)") }
        contexto.render(mascara.applyingFilter("CIFalseColor", parameters: [
            "inputColor0": CIColor.black, "inputColor1": CIColor.white]), to: saida)
        // guarda o quadro já pronto (não a cadeia de filtros), para não ficar mais lento a cada quadro
        mascaraAnterior = CIImage(cvPixelBuffer: saida)
        while !e.isReadyForMoreMediaData { usleep(2000) }
        a.append(saida, withPresentationTime: CMTime(value: indice, timescale: CMTimeScale(fps.rounded())))
    }
    indice += 1
    if indice % 150 == 0 { FileHandle.standardError.write("  \(indice) quadros (\(Int(t)) s)\n".data(using: .utf8)!) }
}

if leitor.status == .failed { sair("Falha ao ler o vídeo: \(leitor.error?.localizedDescription ?? "?")") }
if let g = gravador, let e = entradaGravador {
    e.markAsFinished()
    await g.finishWriting()
    if g.status != .completed { sair("Falha ao gravar o matte: \(g.error?.localizedDescription ?? "?")") }
}

let resultado: [String: Any] = [
    "largura": W, "altura": H, "fps": fps, "inicio": inicio, "fim": (fim * 1000).rounded() / 1000,
    "matte": soRostos ? NSNull() : "matte.mp4" as Any,
    "quadros": quadros,
]
try JSONSerialization.data(withJSONObject: resultado, options: [.sortedKeys]).write(to: arquivoRostos)
let comRosto = quadros.filter { !($0["rosto"] is NSNull) }.count
print("ok · \(quadros.count) quadros · rosto em \(comRosto) · \(soRostos ? "só rostos" : "matte.mp4 + rostos.json") em \(pasta.path)")
