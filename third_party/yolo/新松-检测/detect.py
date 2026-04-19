import argparse
import warnings
from pathlib import Path

from ultralytics import YOLO

warnings.filterwarnings("ignore")

SCRIPT_DIR = Path(__file__).resolve().parent


def _pick_default_weights() -> Path:
    preferred = [
        SCRIPT_DIR / "使用此权重" / "best_fp32.pt",
        SCRIPT_DIR / "使用此权重" / "best_fp32",
        SCRIPT_DIR / "yolo11m.pt",
        SCRIPT_DIR / "yolo11s.pt",
        SCRIPT_DIR / "yolo11n.pt",
    ]
    for candidate in preferred:
        if candidate.exists():
            return candidate
    return SCRIPT_DIR / "yolo11m.pt"


def _resolve_source(source: str):
    if source.isdigit():
        return int(source)
    if "://" in source:
        return source
    return str((SCRIPT_DIR / source).resolve())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="YOLO 快速推理脚本")
    parser.add_argument(
        "--weights",
        default=str(_pick_default_weights()),
        help="模型权重路径，默认优先使用仓库内的自定义权重，否则回退到 yolo11m.pt",
    )
    parser.add_argument(
        "--source",
        default="dataset/images/val",
        help="检测源。支持相对路径、绝对路径、摄像头编号(如 0) 或流地址。",
    )
    parser.add_argument("--imgsz", type=int, default=640, help="图片尺寸")
    parser.add_argument("--project", default="runs/detect-industry", help="结果输出目录")
    parser.add_argument("--name", default="exp_test", help="结果子目录名")
    parser.add_argument("--save", action="store_true", help="保存检测结果")
    parser.add_argument("--conf", type=float, default=None, help="置信度阈值")
    parser.add_argument("--iou", type=float, default=None, help="NMS IOU 阈值")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    weights_path = Path(args.weights).expanduser()
    if not weights_path.is_absolute():
        weights_path = (SCRIPT_DIR / weights_path).resolve()

    model = YOLO(str(weights_path))

    predict_kwargs = {
        "source": _resolve_source(args.source),
        "imgsz": args.imgsz,
        "project": str((SCRIPT_DIR / args.project).resolve()),
        "name": args.name,
        "save": args.save,
    }
    if args.conf is not None:
        predict_kwargs["conf"] = args.conf
    if args.iou is not None:
        predict_kwargs["iou"] = args.iou

    model.predict(**predict_kwargs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
