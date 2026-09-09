import sys
from importlib import import_module
from importlib.metadata import version

import cv2
import gtsam
import matplotlib
import numpy as np
import onnx
import onnxruntime as ort
import pandas
import pytest
import scipy
import torch
import torchvision
from onnx import TensorProto, helper

assert sys.version_info[:2] == (3, 12), sys.version
np.testing.assert_allclose(gtsam.Pose3().matrix(), np.eye(4))
for package, module in (
    ("gtsam", "gtsam"),
    ("pyceres", "pyceres"),
    ("pypcd4", "pypcd4"),
    ("rerun-sdk", "rerun"),
    ("rosbags", "rosbags.highlevel"),
):
    import_module(module)
    print(package, version(package))
for module in (cv2, matplotlib, pandas, pytest, scipy, torch, torchvision, ort):
    print(module.__name__, module.__version__)
gpu = "--gpu" in sys.argv
if gpu:
    assert torch.cuda.is_available(), (
        "CUDA is unavailable; check host driver and GPU allocation"
    )
    props = torch.cuda.get_device_properties(0)
    print(f"GPU: {props.name}, VRAM: {props.total_memory / 2**30:.2f} GiB")
    assert (torch.ones(2, device="cuda") + 1).cpu().tolist() == [2.0, 2.0]
    ort.preload_dlls()

graph = helper.make_graph(
    [helper.make_node("Add", ["x", "x"], ["y"])],
    "smoke",
    [helper.make_tensor_value_info("x", TensorProto.FLOAT, [2])],
    [helper.make_tensor_value_info("y", TensorProto.FLOAT, [2])],
)
model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)])
model.ir_version = 9
onnx.checker.check_model(model)
provider = "CUDAExecutionProvider" if gpu else "CPUExecutionProvider"
session = ort.InferenceSession(model.SerializeToString(), providers=[provider])
assert provider in session.get_providers(), session.get_providers()
np.testing.assert_array_equal(
    session.run(None, {"x": np.ones(2, dtype=np.float32)})[0], [2, 2]
)
print("Python/ONNX smoke passed")
