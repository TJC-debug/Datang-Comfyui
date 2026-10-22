"""Read-only local model verification; never downloads or changes weights."""
import argparse
import hashlib
import json
from pathlib import Path

def verify(root):
    manifest = json.loads(Path(__file__).with_name("skin-model-manifest.json").read_text(encoding="utf-8"))
    for row in manifest["files"]:
        path = root / row["path"]
        if not path.is_file() or path.stat().st_size != row["bytes"]:
            raise ValueError("模型文件缺失或大小不同：" + row["path"])
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest() != row["sha256"]:
            raise ValueError("模型哈希不同：" + row["path"])
    return len(manifest["files"])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-root", type=Path, required=True)
    args = parser.parse_args()
    print("本地模型只读核对通过：", verify(args.model_root), "个文件；未下载或安装。")
