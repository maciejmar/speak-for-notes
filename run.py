"""
Punkt startowy notatnika głosowego.

Uruchomienie:
    poetry run python run.py

Uruchamia:
  1. Sprawdza wymagania (Qdrant, klucze API)
  2. Tworzy katalogi danych
  3. Inicjalizuje kolekcję Qdrant
  4. Startuje serwer FastAPI (uvicorn)
  5. Wyświetla URL z kodem QR dla urządzeń mobilnych
"""

import asyncio
import os
import socket
import sys
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

load_dotenv()

# Dodaj katalog projektu do PATH
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import settings


def check_api_keys() -> bool:
    if not settings.openai_api_key:
        print("\n❌ Brakujący klucz: OPENAI_API_KEY (wymagany dla Whisper + embeddingi)")
        print("   Uzupełnij w .env\n")
        return False
    return True


def create_data_dirs() -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    print(f"✅ Katalog danych: {settings.data_dir.resolve()}")


def init_qdrant() -> bool:
    try:
        client = QdrantClient(
            host=settings.qdrant_host, port=settings.qdrant_port, timeout=3
        )
        collections = client.get_collections().collections
        names = [c.name for c in collections]

        if settings.qdrant_collection not in names:
            client.create_collection(
                collection_name=settings.qdrant_collection,
                vectors_config=VectorParams(
                    size=settings.embedding_size, distance=Distance.COSINE
                ),
            )
            print(f"✅ Kolekcja Qdrant '{settings.qdrant_collection}' utworzona.")
        else:
            print(f"✅ Kolekcja Qdrant '{settings.qdrant_collection}' gotowa.")

        client.close()
        return True

    except Exception as e:
        print(f"⚠️  Qdrant niedostępny ({e})")
        print(
            "   Uruchom: docker compose up -d\n"
            "   Aplikacja działa bez RAG (fallback na JSON)."
        )
        return False


def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"


def print_qr(url: str) -> None:
    try:
        import qrcode

        qr = qrcode.QRCode(border=1)
        qr.add_data(url)
        qr.make(fit=True)
        qr.print_ascii(invert=True)
    except ImportError:
        pass


def main() -> None:
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  🎙️  Notatnik Głosowy AI  ")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    if not check_api_keys():
        sys.exit(1)

    create_data_dirs()
    init_qdrant()

    local_ip = get_local_ip()
    api_url = f"http://{local_ip}:{settings.port}"

    # Sprawdź czy Angular PWA jest zbudowany (cd frontend && npm run build:prod)
    pwa_dist = PROJECT_ROOT / "frontend" / "dist" / "speak-for-notes" / "browser"
    pwa_built = pwa_dist.exists()

    mobile_url = api_url  # PWA serwowane z backendu na tym samym porcie
    dev_frontend = f"http://{local_ip}:4200"

    print(f"\n🌐 Backend API:    http://localhost:{settings.port}")
    print(f"📚 Swagger UI:    http://localhost:{settings.port}/docs")

    if pwa_built:
        print(f"\n✅ PWA zbudowane – aplikacja dostępna pod:")
        print(f"   📱 {mobile_url}  (telefon + instalacja PWA)")
        print(f"\n📱 Zeskanuj QR kod telefonem i zainstaluj PWA:")
        print_qr(mobile_url)
    else:
        print(f"\n⚠️  PWA nie zbudowane. Uruchom frontend dev server:")
        print(f"   cd frontend && npm install && npm start")
        print(f"   📱 Dev frontend: {dev_frontend}")
        print(f"\n   Lub zbuduj PWA (dla instalacji na telefonie):")
        print(f"   cd frontend && npm run build:prod")
        print(f"\n📱 Zeskanuj QR kod (dev server):")
        print_qr(dev_frontend)

    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("Ctrl+C aby zatrzymać\n")

    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
