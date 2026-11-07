import argparse
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent / "app"


def main() -> None:
    parser = argparse.ArgumentParser(description="Добрый город — портал волонтёрских акций")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    sys.path.insert(0, str(APP_DIR))
    import uvicorn
    from main import app
    print(f"Добрый город: http://{args.host}:{args.port}  (координатор: coordinator / Dobro2026!)")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
