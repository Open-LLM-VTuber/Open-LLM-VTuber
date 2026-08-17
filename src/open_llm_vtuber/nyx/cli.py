from __future__ import annotations

from .runtime import NyxRuntime


def main() -> None:
    runtime = NyxRuntime(allowed_roots=["."])
    print("Nyx runtime initialized")
    print(runtime.snapshot())


if __name__ == "__main__":
    main()
