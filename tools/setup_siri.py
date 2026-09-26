import argparse
import secrets
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"


def read_env(lines: list[str]) -> dict[str, str]:
    result = {}
    for line in lines:
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            result[key.strip()] = value.strip()
    return result


def set_value(lines: list[str], key: str, value: str) -> None:
    replacement = f"{key}={value}"
    for index, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[index] = replacement
            return
    lines.append(replacement)


def main() -> None:
    parser = argparse.ArgumentParser(description="Configure the private Siri expense endpoint.")
    parser.add_argument("user_id", type=int)
    parser.add_argument("--rotate", action="store_true")
    args = parser.parse_args()

    lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    values = read_env(lines)
    token = values.get("SIRI_API_TOKEN")
    if args.rotate or not token:
        token = secrets.token_urlsafe(32)

    set_value(lines, "SIRI_API_TOKEN", token)
    set_value(lines, "SIRI_USER_ID", str(args.user_id))
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Siri configuration saved to .env")


if __name__ == "__main__":
    main()
