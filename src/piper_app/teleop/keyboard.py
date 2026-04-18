import argparse
import math
import select
import sys
import time
from contextlib import contextmanager
from platform import system
from typing import List, Optional, Tuple

from piper_app.robot.client import PiperRobotClient
from piper_app.robot.factory import PiperConnectionConfig
from piper_app.robot.safety import clamp_tcp_pose, wait_bool


DEFAULT_POS_STEP_M = 0.005
DEFAULT_ROT_STEP_DEG = 2.0
DEFAULT_SPEED_PERCENT = 10
DEFAULT_REFRESH_HZ = 5.0


def format_pose(pose: Optional[List[float]]) -> str:
    if pose is None:
        return "None"
    return (
        f"x={pose[0]: .4f}  y={pose[1]: .4f}  z={pose[2]: .4f}  "
        f"roll={pose[3]: .3f}  pitch={pose[4]: .3f}  yaw={pose[5]: .3f}"
    )


@contextmanager
def raw_terminal_mode():
    if system() == "Windows":
        yield
        return
    if not sys.stdin.isatty():
        yield
        return

    import termios
    import tty

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        yield
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def read_key(timeout: float) -> Optional[str]:
    if system() == "Windows":
        import msvcrt

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if msvcrt.kbhit():
                ch = msvcrt.getwch()
                if ch in ("\x00", "\xe0") and msvcrt.kbhit():
                    msvcrt.getwch()
                    return None
                return ch
            time.sleep(0.01)
        return None

    if not sys.stdin.isatty():
        time.sleep(timeout)
        return None

    ready, _, _ = select.select([sys.stdin], [], [], timeout)
    if not ready:
        return None
    ch = sys.stdin.read(1)
    if ch == "\x03":
        raise KeyboardInterrupt
    return ch


def clear_screen() -> None:
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def print_ui(
    *,
    args: argparse.Namespace,
    firmware_info: dict,
    control_enabled: bool,
    target_tcp_pose: List[float],
    measured_tcp_pose: Optional[List[float]],
    enabled_list: List[bool],
    robot_status,
    last_action: str,
) -> None:
    clear_screen()
    software_version = firmware_info.get("software_version", "unknown")
    print("Piper TCP Keyboard Teleop")
    print(
        f"robot={args.robot}  channel={args.channel}  firmware={software_version}  "
        f"speed={args.speed_percent}%  dry_run={args.dry_run}"
    )
    print(
        f"control_enabled={control_enabled}  joint_enabled={enabled_list}  "
        f"pos_step={args.pos_step:.4f} m  rot_step={args.rot_step_deg:.2f} deg"
    )
    if robot_status is not None:
        print(
            f"arm_status={robot_status.msg.arm_status}  "
            f"mode_feedback={robot_status.msg.mode_feedback}  "
            f"motion_status={robot_status.msg.motion_status}"
        )
    else:
        print("arm_status=None")
    print()
    print("Measured TCP Pose:")
    print(f"  {format_pose(measured_tcp_pose)}")
    print("Target TCP Pose:")
    print(f"  {format_pose(target_tcp_pose)}")
    print()
    print("Controls:")
    print("  w/s: x+/-    a/d: y+/-    r/f: z+/-")
    print("  u/o: roll-/+ i/k: pitch+/- j/l: yaw-/+")
    print("  -/=: pos step down/up    [ / ]: rot step down/up")
    print("  t: sync target to current TCP pose")
    print("  e: enable all joints     n: disable all joints")
    print("  b: electronic emergency stop")
    print("  h: print help/action     q: quit")
    print()
    print(f"Last action: {last_action}")


def apply_motion(robot, target_tcp_pose: List[float], dry_run: bool) -> str:
    if dry_run:
        return "Dry-run: target updated, motion not sent."
    flange_pose = robot.get_tcp2flange_pose(target_tcp_pose)
    robot.move_p(flange_pose)
    return "move_p sent."


def run(args: argparse.Namespace) -> None:
    args.refresh_hz = max(1.0, args.refresh_hz)
    args.pos_step = max(0.0005, args.pos_step)
    args.rot_step_deg = max(0.1, args.rot_step_deg)
    args.speed_percent = max(1, min(100, args.speed_percent))

    client = PiperRobotClient(
        PiperConnectionConfig(
            robot=args.robot,
            interface=args.interface,
            channel=args.channel,
            bitrate=args.bitrate,
            firmware_timeout=args.firmware_timeout,
            speed_percent=args.speed_percent,
            tcp_offset=list(args.tcp_offset),
        )
    )
    client.connect()
    robot = client.robot
    try:
        measured_tcp = client.get_tcp_pose()
        if measured_tcp is None:
            raise RuntimeError("Failed to read current TCP pose.")

        target_tcp_pose = clamp_tcp_pose(measured_tcp)
        last_action = (
            "Connected. Motion commands are blocked until you press 'e' to enable control."
        )
        control_enabled = False
        refresh_interval = 1.0 / args.refresh_hz

        with raw_terminal_mode():
            while True:
                measured_tcp_pose = client.get_tcp_pose()
                enabled_list = client.get_enabled_list()
                robot_status = client.get_arm_status()

                print_ui(
                    args=args,
                    firmware_info=client.firmware_info,
                    control_enabled=control_enabled,
                    target_tcp_pose=target_tcp_pose,
                    measured_tcp_pose=measured_tcp_pose,
                    enabled_list=enabled_list,
                    robot_status=robot_status,
                    last_action=last_action,
                )

                key = read_key(refresh_interval)
                if key is None:
                    continue

                if key in ("q", "Q"):
                    break

                if key in ("h", "H"):
                    last_action = "Help refreshed."
                    continue

                if key in ("e", "E"):
                    client.enable()
                    ok = wait_bool(lambda: all(client.get_enabled_list()))
                    control_enabled = ok
                    last_action = "All joints enabled." if ok else "Enable timeout."
                    continue

                if key in ("n", "N"):
                    client.disable()
                    ok = wait_bool(lambda: not any(client.get_enabled_list()))
                    control_enabled = False
                    last_action = "All joints disabled." if ok else "Disable timeout."
                    continue

                if key in ("b", "B"):
                    client.electronic_emergency_stop()
                    control_enabled = False
                    last_action = "Electronic emergency stop sent. Re-enable before moving again."
                    continue

                if key in ("t", "T"):
                    measured_tcp = client.get_tcp_pose()
                    if measured_tcp is None:
                        last_action = "Failed to sync target: TCP pose unavailable."
                    else:
                        target_tcp_pose = clamp_tcp_pose(measured_tcp)
                        last_action = "Target pose synced to current TCP pose."
                    continue

                if key == "-":
                    args.pos_step = max(0.0005, args.pos_step * 0.5)
                    last_action = f"Position step updated to {args.pos_step:.4f} m."
                    continue

                if key == "=":
                    args.pos_step = min(0.05, args.pos_step * 2.0)
                    last_action = f"Position step updated to {args.pos_step:.4f} m."
                    continue

                if key == "[":
                    args.rot_step_deg = max(0.1, args.rot_step_deg * 0.5)
                    last_action = f"Rotation step updated to {args.rot_step_deg:.2f} deg."
                    continue

                if key == "]":
                    args.rot_step_deg = min(30.0, args.rot_step_deg * 2.0)
                    last_action = f"Rotation step updated to {args.rot_step_deg:.2f} deg."
                    continue

                if not control_enabled:
                    last_action = "Motion blocked. Press 'e' to enable all joints first."
                    continue

                if not all(enabled_list):
                    control_enabled = False
                    last_action = "Motion blocked. Some joints are not enabled."
                    continue

                delta_pos = args.pos_step
                delta_rot = math.radians(args.rot_step_deg)
                new_target = target_tcp_pose[:]
                action_name = None

                if key == "w":
                    new_target[0] += delta_pos
                    action_name = "x+"
                elif key == "s":
                    new_target[0] -= delta_pos
                    action_name = "x-"
                elif key == "a":
                    new_target[1] += delta_pos
                    action_name = "y+"
                elif key == "d":
                    new_target[1] -= delta_pos
                    action_name = "y-"
                elif key == "r":
                    new_target[2] += delta_pos
                    action_name = "z+"
                elif key == "f":
                    new_target[2] -= delta_pos
                    action_name = "z-"
                elif key == "u":
                    new_target[3] -= delta_rot
                    action_name = "roll-"
                elif key == "o":
                    new_target[3] += delta_rot
                    action_name = "roll+"
                elif key == "i":
                    new_target[4] += delta_rot
                    action_name = "pitch+"
                elif key == "k":
                    new_target[4] -= delta_rot
                    action_name = "pitch-"
                elif key == "j":
                    new_target[5] -= delta_rot
                    action_name = "yaw-"
                elif key == "l":
                    new_target[5] += delta_rot
                    action_name = "yaw+"
                else:
                    last_action = f"Ignored key: {repr(key)}"
                    continue

                new_target = clamp_tcp_pose(new_target)
                try:
                    motion_result = apply_motion(robot, new_target, args.dry_run)
                except Exception as exc:
                    last_action = f"Motion failed: {type(exc).__name__}: {exc}"
                    continue

                target_tcp_pose = new_target
                last_action = f"{action_name} -> {motion_result}"
    finally:
        client.disconnect()
