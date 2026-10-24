# -*- coding: utf-8 -*-
"""
Worker autónomo de inferencia de voz para DDEV Studio.
Se ejecuta en el entorno virtual aislado (~/.local/share/ddev-studio/voice/venv)
para aislar las dependencias pesadas de ML (faster-whisper, kokoro-onnx, soundfile)
del proceso principal de GTK3.
"""

import argparse
import json
import os
import sys


def handle_check():
    """Verifica si las librerías necesarias están instaladas en el entorno."""
    result = {
        "ok": True,
        "whisper_installed": False,
        "kokoro_installed": False,
        "soundfile_installed": False,
        "error": None
    }
    try:
        import faster_whisper
        result["whisper_installed"] = True
    except Exception as ex:
        result["ok"] = False
        result["error"] = f"faster-whisper no disponible: {ex}"

    try:
        import kokoro_onnx
        result["kokoro_installed"] = True
    except Exception as ex:
        result["ok"] = False
        err = f"kokoro-onnx no disponible: {ex}"
        result["error"] = f"{result['error']}; {err}" if result.get("error") else err

    try:
        import soundfile
        result["soundfile_installed"] = True
    except Exception as ex:
        result["ok"] = False
        err = f"soundfile no disponible: {ex}"
        result["error"] = f"{result['error']}; {err}" if result.get("error") else err

    print(json.dumps(result, ensure_ascii=False))


def handle_transcribe(args):
    """Transcribe un archivo de audio WAV a texto en español usando faster-whisper."""
    if not os.path.isfile(args.audio):
        print(json.dumps({"ok": False, "error": f"Archivo de audio no existe: {args.audio}"}))
        sys.exit(1)

    try:
        from faster_whisper import WhisperModel

        model_size = args.model or "base"
        model = WhisperModel(model_size, device="cpu", compute_type="int8")

        segments, info = model.transcribe(
            args.audio,
            language=args.lang or "es",
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
        )

        texts = []
        for segment in segments:
            clean = segment.text.strip()
            if clean:
                texts.append(clean)

        full_text = " ".join(texts).strip()

        print(json.dumps({
            "ok": True,
            "text": full_text,
            "language": info.language,
            "probability": info.language_probability
        }, ensure_ascii=False))

    except Exception as ex:
        print(json.dumps({"ok": False, "error": str(ex)}, ensure_ascii=False))
        sys.exit(1)


def handle_synthesize(args):
    """Sintetiza texto a voz en formato WAV usando Kokoro-82M ONNX."""
    if not args.text or not args.text.strip():
        print(json.dumps({"ok": False, "error": "El texto a sintetizar no puede estar vacío."}))
        sys.exit(1)

    if not os.path.isfile(args.model_path):
        print(json.dumps({"ok": False, "error": f"Modelo Kokoro ONNX no encontrado en: {args.model_path}"}))
        sys.exit(1)

    if not os.path.isfile(args.voices_path):
        print(json.dumps({"ok": False, "error": f"Archivo de voces Kokoro no encontrado en: {args.voices_path}"}))
        sys.exit(1)

    try:
        import soundfile as sf
        from kokoro_onnx import Kokoro

        kokoro = Kokoro(args.model_path, args.voices_path)
        voice = args.voice or "ef_dora"
        speed = float(args.speed or 1.0)
        lang = args.lang or "es"

        # Limitar longitud para evitar saturación de memoria si el texto es gigantesco
        clean_text = args.text.strip()
        if len(clean_text) > 4000:
            clean_text = clean_text[:4000] + "..."

        samples, sample_rate = kokoro.create(
            clean_text,
            voice=voice,
            speed=speed,
            lang=lang
        )

        output_path = args.output
        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        sf.write(output_path, samples, sample_rate)

        duration_sec = len(samples) / float(sample_rate) if sample_rate else 0.0

        print(json.dumps({
            "ok": True,
            "output": output_path,
            "duration": round(duration_sec, 2),
            "sample_rate": sample_rate
        }, ensure_ascii=False))

    except Exception as ex:
        print(json.dumps({"ok": False, "error": str(ex)}, ensure_ascii=False))
        sys.exit(1)


def handle_daemon(args):
    """
    Modo demonio persistente en RAM.
    Carga el modelo Kokoro ONNX una sola vez en memoria y atiende solicitudes
    de síntesis ultra rápidas (< 200 ms por frase) a través de stdin/stdout.
    """
    if not os.path.isfile(args.model_path):
        print(json.dumps({"ok": False, "error": f"Modelo no existe: {args.model_path}"}), flush=True)
        sys.exit(1)
    if not os.path.isfile(args.voices_path):
        print(json.dumps({"ok": False, "error": f"Voces no existen: {args.voices_path}"}), flush=True)
        sys.exit(1)

    try:
        import soundfile as sf
        from kokoro_onnx import Kokoro

        kokoro = Kokoro(args.model_path, args.voices_path)
        # Notificar a DDEV Studio que el modelo está caliente y listo en RAM
        print(json.dumps({"status": "ready"}), flush=True)
    except Exception as ex:
        print(json.dumps({"ok": False, "error": f"Fallo al cargar Kokoro en RAM: {ex}"}), flush=True)
        sys.exit(1)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            action = req.get("action")
            req_id = req.get("id")

            if action == "synthesize":
                text = req.get("text", "").strip()
                output_path = req.get("output")
                voice = req.get("voice", "ef_dora")
                speed = float(req.get("speed", 1.0))
                lang = req.get("lang", "es")

                if not text or not output_path:
                    print(json.dumps({"ok": False, "id": req_id, "error": "Parámetros incompletos"}), flush=True)
                    continue

                samples, sample_rate = kokoro.create(text, voice=voice, speed=speed, lang=lang)
                out_dir = os.path.dirname(output_path)
                if out_dir:
                    os.makedirs(out_dir, exist_ok=True)
                sf.write(output_path, samples, sample_rate)
                duration_sec = len(samples) / float(sample_rate) if sample_rate else 0.0

                print(json.dumps({
                    "ok": True,
                    "id": req_id,
                    "output": output_path,
                    "duration": round(duration_sec, 2),
                    "sample_rate": sample_rate
                }), flush=True)

            elif action == "ping":
                print(json.dumps({"ok": True, "id": req_id, "pong": True}), flush=True)

            elif action == "exit":
                break

        except Exception as ex:
            req_id = req.get("id") if "req" in locals() and isinstance(req, dict) else None
            print(json.dumps({"ok": False, "id": req_id, "error": str(ex)}), flush=True)


def main():
    parser = argparse.ArgumentParser(description="DDEV Studio Voice AI Worker")
    subparsers = parser.add_subparsers(dest="command")

    # Comando check
    subparsers.add_parser("check", help="Comprueba instalación de dependencias")

    # Comando transcribe
    p_trans = subparsers.add_parser("transcribe", help="Transcribe audio a texto")
    p_trans.add_argument("--audio", required=True, help="Ruta al archivo WAV")
    p_trans.add_argument("--model", default="base", help="Tamaño modelo Whisper (tiny, base, small)")
    p_trans.add_argument("--lang", default="es", help="Código de idioma (ej. es)")

    # Comando synthesize
    p_synth = subparsers.add_parser("synthesize", help="Sintetiza texto a audio WAV")
    p_synth.add_argument("--text", required=True, help="Texto a leer")
    p_synth.add_argument("--output", required=True, help="Ruta del archivo WAV de salida")
    p_synth.add_argument("--model-path", required=True, help="Ruta del archivo kokoro-v1.0.onnx")
    p_synth.add_argument("--voices-path", required=True, help="Ruta del archivo voices-v1.0.bin")
    p_synth.add_argument("--voice", default="ef_dora", help="Identificador de voz (ef_dora, em_alex, em_santa)")
    p_synth.add_argument("--speed", type=float, default=1.0, help="Velocidad de reproducción (0.8 - 1.5)")
    p_synth.add_argument("--lang", default="es", help="Código de idioma (es)")

    # Comando daemon (Residente en RAM para latencia cero)
    p_daemon = subparsers.add_parser("daemon", help="Inicia worker en modo demonio persistente en RAM")
    p_daemon.add_argument("--model-path", required=True, help="Ruta al modelo ONNX")
    p_daemon.add_argument("--voices-path", required=True, help="Ruta al binario de voces")

    args = parser.parse_args()

    if args.command == "check":
        handle_check()
    elif args.command == "transcribe":
        handle_transcribe(args)
    elif args.command == "synthesize":
        handle_synthesize(args)
    elif args.command == "daemon":
        handle_daemon(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
