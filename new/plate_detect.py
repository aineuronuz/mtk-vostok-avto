"""Номера на фото машин из объявлений: детектор китайских номеров HyperLPR3 (y5fu, ONNX, Apache-2.0; модели —
~/yurazol-sites/tools/plate_models) находит рамку и четыре угла номера; на его место — табличка «ВОСТОК-АВТО» тем же
plate_tool.overlay, что в каталогах и КП МТК (Юрий 26.10.2026: номера на фото закрыты).
cover(src, dst) -> число закрытых номеров."""
from pathlib import Path

import numpy as np

MODELS = Path.home() / "yurazol-sites" / "tools" / "plate_models"
SIZE = 640
_S = {}


def _session():
    if "s" not in _S:
        import onnxruntime as ort
        _S["s"] = ort.InferenceSession(str(MODELS / f"y5fu_{SIZE}x_sim.onnx"), providers=["CPUExecutionProvider"])
    return _S["s"]


def _letter(img):
    import cv2
    h, w = img.shape[:2]
    r = min(SIZE / h, SIZE / w)
    nh, nw = int(h * r), int(w * r)
    top, left = (SIZE - nh) // 2, (SIZE - nw) // 2
    out = cv2.copyMakeBorder(cv2.resize(img, (nw, nh)), top, SIZE - nh - top, left, SIZE - nw - left, cv2.BORDER_CONSTANT, value=(0, 0, 0))
    return out, r, left, top


def _nms(b, thr):
    idx, keep = np.argsort(b[:, 4])[::-1], []
    while idx.size:
        i = idx[0]
        keep.append(i)
        x1, y1 = np.maximum(b[i, 0], b[idx[1:], 0]), np.maximum(b[i, 1], b[idx[1:], 1])
        x2, y2 = np.minimum(b[i, 2], b[idx[1:], 2]), np.minimum(b[i, 3], b[idx[1:], 3])
        inter = np.maximum(0, x2 - x1) * np.maximum(0, y2 - y1)
        area = lambda k: (b[k, 2] - b[k, 0]) * (b[k, 3] - b[k, 1])
        iou = inter / (area(i) + area(idx[1:]) - inter)
        idx = idx[np.where(iou <= thr)[0] + 1]
    return keep


def detect(img_bgr, conf=0.35):
    """[(score, [[x,y]×4] — углы по часовой от левого верхнего)] на исходном кадре."""
    x, r, left, top = _letter(img_bgr)
    x = x[:, :, ::-1].transpose(2, 0, 1)[None].astype(np.float32) / 255
    s = _session()
    d = s.run(None, {s.get_inputs()[0].name: x})[0][0]
    d = d[d[:, 4] > conf]
    if not len(d):
        return []
    d[:, 13:15] *= d[:, 4:5]
    xy = d[:, :4].copy()
    xy[:, 0], xy[:, 1], xy[:, 2], xy[:, 3] = d[:, 0] - d[:, 2] / 2, d[:, 1] - d[:, 3] / 2, d[:, 0] + d[:, 2] / 2, d[:, 1] + d[:, 3] / 2
    out = np.concatenate((xy, d[:, 13:15].max(1, keepdims=True), d[:, 5:13]), 1)
    out = out[_nms(out, 0.5)]
    out[:, [0, 2, 5, 7, 9, 11]] = (out[:, [0, 2, 5, 7, 9, 11]] - left) / r
    out[:, [1, 3, 6, 8, 10, 12]] = (out[:, [1, 3, 6, 8, 10, 12]] - top) / r
    return [(float(o[4]), [[float(o[5 + 2 * k]), float(o[6 + 2 * k])] for k in range(4)]) for o in out if o[4] > conf]


def cover(src, dst):
    """Фото src → dst (JPEG) с табличкой «ВОСТОК-АВТО» на месте каждого найденного номера."""
    import sys
    import cv2
    from PIL import Image
    sys.path.insert(0, str(Path.home() / "auto-china" / "catalog"))
    import plate_tool
    plate_tool.TEXT = "ВОСТОК-АВТО"
    im = Image.open(src).convert("RGB")
    found = detect(cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR))
    for _, q in found:
        im = plate_tool.overlay(im, [[round(x), round(y)] for x, y in q], aspect=3.14).convert("RGB")
    im.save(dst, "JPEG", quality=88)
    return len(found)
