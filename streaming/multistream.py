import argparse
import subprocess
from typing import List


def start_multistream(input_source: str, rtmp_urls: List[str]) -> None:
    """Stream input source to multiple RTMP endpoints using ffmpeg."""
    if not rtmp_urls:
        raise ValueError("No RTMP URLs provided")
    outputs = "|".join(f"[f=flv]{url}" for url in rtmp_urls)
    cmd = [
        "ffmpeg",
        "-re",
        "-i",
        input_source,
        "-c:v",
        "copy",
        "-c:a",
        "copy",
        "-f",
        "tee",
        outputs,
    ]
    subprocess.run(cmd, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Multi-platform livestream helper")
    parser.add_argument("input", help="Input video source (file path or URL)")
    parser.add_argument("--rtmp", nargs="+", required=True, help="RTMP URLs")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    start_multistream(args.input, args.rtmp)
