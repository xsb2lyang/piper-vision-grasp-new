from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import numpy as np
import yaml

from piper_app.calibration.session import resolve_repo_path
from piper_app.calibration.transforms import compose_matrix, pose6_to_matrix
from piper_app.config import load_project_defaults
from piper_app.keypoints.store import find_record, load_keypoint_config, parse_keypoint_records


@dataclass
class PickDemoPose:
    name: str
    tcp_pose: list[float]
    joint_angles: list[float]


@dataclass
class PickDemoWorkspace:
    config_path: str
    handeye_path: str
    robot: str
    can: dict[str, Any]
    tcp_offset: list[float]
    task_defaults: dict[str, Any]
    home: PickDemoPose
    observe: PickDemoPose
    drop_pose: PickDemoPose
    extras: dict[str, PickDemoPose]
    T_tcp_camera: np.ndarray


@dataclass
class PickPlan:
    selected_pixel: tuple[int, int]
    camera_point_m: tuple[float, float, float]
    base_point_m: tuple[float, float, float]
    pregrasp_pose: list[float]
    grasp_pose: list[float]
    lift_pose: list[float]
    drop_prepose: list[float]
    drop_pose: list[float]


def _default_task_values(raw_defaults: dict[str, Any]) -> dict[str, Any]:
    task_defaults = dict(raw_defaults)
    task_defaults.setdefault("pick_point_offset_m", [0.0, 0.0, 0.0])
    task_defaults.setdefault("pregrasp_offset_m", [0.0, 0.0, 0.08])
    task_defaults.setdefault("descend_distance_m", 0.08)
    task_defaults.setdefault("grasp_linear_move", False)
    task_defaults.setdefault("lift_distance_m", 0.10)
    task_defaults.setdefault("drop_offset_m", [0.0, 0.0, 0.20])
    task_defaults.setdefault("gripper_open_width_m", 0.0)
    task_defaults.setdefault("gripper_close_width_m", 0.0)
    task_defaults.setdefault("gripper_force_n", 1.0)
    task_defaults.setdefault("gripper_settle_s", 0.8)
    task_defaults.setdefault("gripper_close_steps", 4)
    task_defaults.setdefault("gripper_close_step_pause_s", 0.15)
    task_defaults.setdefault("move_timeout_s", 8.0)
    task_defaults.setdefault("place_timeout_s", 15.0)
    task_defaults.setdefault("place_linear_move", False)
    task_defaults.setdefault("retreat_linear_move", False)
    task_defaults.setdefault("workspace_min_m", [-0.05, -0.40, 0.00])
    task_defaults.setdefault("workspace_max_m", [0.45, 0.40, 0.45])
    task_defaults.setdefault("observe_tolerance_translation_m", 0.03)
    task_defaults.setdefault("observe_tolerance_rotation_deg", 10.0)
    return task_defaults


def load_handeye_matrix(path_like: str) -> np.ndarray:
    path = resolve_repo_path(path_like)
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    matrix = payload.get("T_tcp_camera", {}).get("matrix")
    if not matrix:
        raise ValueError(f"Hand-eye file at {path} does not contain T_tcp_camera.matrix.")
    return np.asarray(matrix, dtype=np.float64)


def load_pick_workspace(config_path: str, handeye_path: str) -> PickDemoWorkspace:
    defaults = load_project_defaults()["task"]
    requested_path = resolve_repo_path(config_path)
    template_path = resolve_repo_path(defaults.get("template_path", "configs/task/pick_demo_template.yaml"))
    active_path = requested_path
    if requested_path.exists():
        payload = load_keypoint_config(requested_path)
    elif template_path.exists():
        payload = load_keypoint_config(template_path)
        active_path = template_path
    else:
        payload = {}
    records = parse_keypoint_records(payload)
    home = find_record(records, "home")
    observe = find_record(records, "observe")
    drop_pose = find_record(records, "drop_pose")
    if home is None or observe is None or drop_pose is None:
        raise ValueError("Keypoint config must contain home, observe, and drop_pose.")

    merged_task_defaults = _default_task_values(defaults.get("task_defaults", {}))
    merged_task_defaults.update(payload.get("task_defaults", {}))
    merged_task_defaults = _default_task_values(merged_task_defaults)

    extras = {
        record.name: PickDemoPose(record.name, record.tcp_pose, record.joint_angles)
        for record in records
        if record.name not in {"home", "observe", "drop_pose"}
    }
    return PickDemoWorkspace(
        config_path=str(active_path),
        handeye_path=str(resolve_repo_path(handeye_path)),
        robot=str(payload.get("robot", defaults.get("robot", "piper"))),
        can=dict(payload.get("can", {})),
        tcp_offset=[float(value) for value in payload.get("tcp_offset", [0.0] * 6)],
        task_defaults=merged_task_defaults,
        home=PickDemoPose(home.name, home.tcp_pose, home.joint_angles),
        observe=PickDemoPose(observe.name, observe.tcp_pose, observe.joint_angles),
        drop_pose=PickDemoPose(drop_pose.name, drop_pose.tcp_pose, drop_pose.joint_angles),
        extras=extras,
        T_tcp_camera=load_handeye_matrix(handeye_path),
    )


def compute_base_point_from_camera(
    tcp_pose6: list[float],
    T_tcp_camera: np.ndarray,
    camera_point_m: tuple[float, float, float],
) -> np.ndarray:
    T_base_tcp = pose6_to_matrix(tcp_pose6)
    T_camera_object = np.eye(4, dtype=np.float64)
    T_camera_object[:3, 3] = np.asarray(camera_point_m, dtype=np.float64)
    T_base_object = compose_matrix(compose_matrix(T_base_tcp, T_tcp_camera), T_camera_object)
    return T_base_object[:3, 3].astype(np.float64)


def build_pick_plan(
    *,
    selected_pixel: tuple[int, int],
    camera_point_m: tuple[float, float, float],
    base_point_m: np.ndarray,
    workspace: PickDemoWorkspace,
) -> PickPlan:
    click_point_offset = np.asarray(
        workspace.task_defaults.get("pick_point_offset_m", [0.0, 0.0, 0.0]),
        dtype=np.float64,
    ).reshape(3)
    base_xyz = np.asarray(base_point_m, dtype=np.float64).reshape(3) + click_point_offset
    orientation = workspace.observe.tcp_pose[3:6]
    pregrasp_offset = np.asarray(workspace.task_defaults["pregrasp_offset_m"], dtype=np.float64).reshape(3)
    drop_offset = np.asarray(
        workspace.task_defaults.get("drop_offset_m", [0.0, 0.0, workspace.task_defaults["lift_distance_m"]]),
        dtype=np.float64,
    ).reshape(3)
    descend_distance = float(workspace.task_defaults["descend_distance_m"])
    lift_distance = float(workspace.task_defaults["lift_distance_m"])

    pregrasp_xyz = base_xyz + pregrasp_offset
    grasp_xyz = pregrasp_xyz + np.array([0.0, 0.0, -descend_distance], dtype=np.float64)
    lift_xyz = grasp_xyz + np.array([0.0, 0.0, lift_distance], dtype=np.float64)

    drop_pose = list(workspace.drop_pose.tcp_pose)
    drop_pose[:3] = (np.asarray(drop_pose[:3], dtype=np.float64) + click_point_offset).tolist()
    drop_prepose = list(drop_pose)
    drop_prepose[:3] = (np.asarray(drop_pose[:3], dtype=np.float64) + drop_offset).tolist()

    pregrasp_pose = pregrasp_xyz.tolist() + list(orientation)
    grasp_pose = grasp_xyz.tolist() + list(orientation)
    lift_pose = lift_xyz.tolist() + list(orientation)

    return PickPlan(
        selected_pixel=(int(selected_pixel[0]), int(selected_pixel[1])),
        camera_point_m=tuple(float(value) for value in camera_point_m),
        base_point_m=tuple(float(value) for value in base_xyz.tolist()),
        pregrasp_pose=[float(value) for value in pregrasp_pose],
        grasp_pose=[float(value) for value in grasp_pose],
        lift_pose=[float(value) for value in lift_pose],
        drop_prepose=[float(value) for value in drop_prepose],
        drop_pose=[float(value) for value in drop_pose],
    )


def validate_workspace_point(base_point_m: tuple[float, float, float], workspace: PickDemoWorkspace) -> Optional[str]:
    workspace_min = np.asarray(workspace.task_defaults["workspace_min_m"], dtype=np.float64).reshape(3)
    workspace_max = np.asarray(workspace.task_defaults["workspace_max_m"], dtype=np.float64).reshape(3)
    point = np.asarray(base_point_m, dtype=np.float64).reshape(3)
    if np.any(point < workspace_min) or np.any(point > workspace_max):
        return (
            "Selected point is outside the configured workspace bounds: "
            f"point={tuple(round(float(v), 4) for v in point.tolist())}"
        )
    return None


def pose_delta(a_pose: list[float], b_pose: list[float]) -> tuple[float, float]:
    a = pose6_to_matrix(a_pose)
    b = pose6_to_matrix(b_pose)
    translation_delta = float(np.linalg.norm(a[:3, 3] - b[:3, 3]))
    rotation_delta = float(
        np.degrees(
            np.arccos(
                max(
                    -1.0,
                    min(1.0, float((np.trace(a[:3, :3].T @ b[:3, :3]) - 1.0) * 0.5)),
                )
            )
        )
    )
    return translation_delta, rotation_delta


def is_near_observe_pose(current_tcp_pose: Optional[list[float]], workspace: PickDemoWorkspace) -> bool:
    if current_tcp_pose is None:
        return False
    translation_delta, rotation_delta = pose_delta(current_tcp_pose, workspace.observe.tcp_pose)
    return (
        translation_delta <= float(workspace.task_defaults["observe_tolerance_translation_m"])
        and rotation_delta <= float(workspace.task_defaults["observe_tolerance_rotation_deg"])
    )
