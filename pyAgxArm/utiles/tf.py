import math
from typing import Tuple

# Define Euler angle order encoding table
_AXES2TUPLE = {
    'sxyz': (0, 0, 0, 0),
    'rzyx': (0, 0, 0, 1),
}
axes = 'sxyz'
# For axis index calculation
_NEXT_AXIS = [1, 2, 0, 1]
# Set floating-point comparison error threshold
_EPS = 1e-10

def normalize_quat(qx, qy, qz, qw):
    norm = math.sqrt(qx**2 + qy**2 + qz**2 + qw**2)
    return qx / norm, qy / norm, qz / norm, qw / norm

def quat_convert_euler(qx: float, qy: float, qz: float, qw: float) -> Tuple[float, float, float]:
                    #    axes: Literal['sxyz', 'rzyx'] = 'sxyz') -> Tuple[float, float, float]:
    """
    Convert quaternion [x, y, z, w] to Euler angles (roll, pitch, yaw).

    Parameters:
        x, y, z, w - Quaternion components
        axes - Euler angle axis order, supports 'sxyz' or 'rzyx'

    Returns:
        tuple(float, float, float): Euler angles (roll, pitch, yaw) in radians
    """
    # Axis order configuration
    try:
        firstaxis, parity, repetition, frame = _AXES2TUPLE[axes.lower()]
    except (KeyError, AttributeError):
        raise ValueError(f"Unsupported axes specification: '{axes}'. "
                        f"Only 'sxyz' and 'rzyx' are currently supported.")
    # Axis indices: x=0, y=1, z=2
    # Get axis order indices
    i = firstaxis
    j = _NEXT_AXIS[i + parity]
    k = _NEXT_AXIS[i - parity + 1]
    qx, qy, qz, qw = normalize_quat(qx, qy, qz, qw)
    # Matrix M[i][j] representation: pre-expanded 3x3 rotation matrix
    M = [[0.0] * 3 for _ in range(3)]
    M[0][0] = 1 - 2*(qy**2 + qz**2)
    M[0][1] =     2*(qx*qy - qz*qw)
    M[0][2] =     2*(qx*qz + qy*qw)
    M[1][0] =     2*(qx*qy + qz*qw)
    M[1][1] = 1 - 2*(qx**2 + qz**2)
    M[1][2] =     2*(qy*qz - qx*qw)
    M[2][0] =     2*(qx*qz - qy*qw)
    M[2][1] =     2*(qy*qz + qx*qw)
    M[2][2] = 1 - 2*(qx**2 + qy**2)

    # Calculate Euler angles
    if repetition:
        sy = math.sqrt(M[i][j] ** 2 + M[i][k] ** 2)
        if sy > _EPS:
            ax = math.atan2(M[i][j], M[i][k])
            ay = math.atan2(sy, M[i][i])
            az = math.atan2(M[j][i], -M[k][i])
        else:
            ax = math.atan2(-M[j][k], M[j][j])
            ay = math.atan2(sy, M[i][i])
            az = 0.0
    else:
        cy = math.sqrt(M[i][i] ** 2 + M[j][i] ** 2)
        if cy > _EPS:
            ax = math.atan2(M[k][j], M[k][k])
            ay = math.atan2(-M[k][i], cy)
            az = math.atan2(M[j][i], M[i][i])
        else:
            ax = math.atan2(-M[j][k], M[j][j])
            ay = math.atan2(-M[k][i], cy)
            az = 0.0

    # Adjust angle directions
    if parity:
        ax, ay, az = -ax, -ay, -az
    if frame:
        ax, az = az, ax

    return ax, ay, az

def euler_convert_quat(roll:float, pitch:float, yaw:float) -> Tuple[float, float, float, float]:
    """
    Convert Euler angles (roll, pitch, yaw) to quaternion.

    Parameters:
        roll  - Rotation angle around X-axis (in radians)
        pitch - Rotation angle around Y-axis (in radians)
        yaw   - Rotation angle around Z-axis (in radians)

    Returns:
        list: Quaternion [x, y, z, w]
    """
    try:
        firstaxis, parity, repetition, frame = _AXES2TUPLE[axes.lower()]
    except (KeyError, AttributeError):
        raise ValueError(f"Unsupported axes specification: '{axes}'. "
                        f"Only 'sxyz' and 'rzyx' are currently supported.")
    # Axis indices: x=0, y=1, z=2
    # Get axis order indices
    i = firstaxis
    j = _NEXT_AXIS[i + parity]
    k = _NEXT_AXIS[i - parity + 1]

    # Coordinate system adjustment
    if frame:
        roll, yaw = yaw, roll
    if parity:
        pitch = -pitch

    # Halve angles
    roll *= 0.5
    pitch *= 0.5
    yaw *= 0.5

    # Trigonometric functions
    c_roll = math.cos(roll)
    s_roll = math.sin(roll)
    c_pitch = math.cos(pitch)
    s_pitch = math.sin(pitch)
    c_yaw = math.cos(yaw)
    s_yaw = math.sin(yaw)

    cc = c_roll * c_yaw
    cs = c_roll * s_yaw
    sc = s_roll * c_yaw
    ss = s_roll * s_yaw

    # Initialize quaternion [x, y, z, w]
    q = [0.0, 0.0, 0.0, 0.0]

    if repetition:
        q[i] = c_pitch * (cs + sc)
        q[j] = s_pitch * (cc + ss)
        q[k] = s_pitch * (cs - sc)
        q[3] = c_pitch * (cc - ss)
    else:
        q[i] = c_pitch * sc - s_pitch * cs
        q[j] = c_pitch * ss + s_pitch * cc
        q[k] = c_pitch * cs - s_pitch * sc
        q[3] = c_pitch * cc + s_pitch * ss

    if parity:
        q[j] *= -1

    return q[0], q[1], q[2], q[3]  # [qx, qy, qz, qw]

def quat_to_euler(q: list, epsilon_deg: float = 0.01) -> Tuple[float, float, float]:
    """
    Convert quaternion to Euler angles using external rotation XYZ order.
    
    This function converts a quaternion [x, y, z, w] to Euler angles (roll, pitch, yaw)
    while avoiding singularities at the critical points (gimbal lock).
    
    Parameters
    ----------
    q : tuple or list
        Quaternion in format [x, y, z, w]
    epsilon_deg : float, optional
        Distance from critical points in degrees (default: 0.01)
    
    Returns
    -------
    tuple
        Euler angles (roll, pitch, yaw) in radians with range limits:
        - roll: (-π + epsilon, π - epsilon)
        - pitch: (-π/2 + epsilon, π/2 - epsilon)
        - yaw: (-π + epsilon, π - epsilon)
    
    Notes
    -----
    The function handles singularity conditions by limiting angles near the
    critical points (±π/2 for pitch) to avoid numerical instability.
    
    Examples
    --------
    >>> quat_to_euler([0, 0, 0, 1])
    (0.0, 0.0, 0.0)
    
    >>> quat_to_euler([0, 0, 0.7071, 0.7071], epsilon_deg=0.5)
    (0.0, 0.0, 1.57075)
    """
    x, y, z, w = q
    
    # Convert to radians
    epsilon = math.radians(epsilon_deg)
    
    # Calculate Euler angles (external rotation XYZ order)
    # roll (x-axis rotation)
    sinr_cosp = 2 * (w * x + y * z)
    cosr_cosp = 1 - 2 * (x * x + y * y)
    roll = math.atan2(sinr_cosp, cosr_cosp)
    
    # pitch (y-axis rotation)
    sinp = 2 * (w * y - z * x)
    if abs(sinp) >= 1:
        # Use sign-preserving asin approximation
        pitch = math.copysign(math.pi / 2, sinp)
    else:
        pitch = math.asin(sinp)
    
    # yaw (z-axis rotation)
    siny_cosp = 2 * (w * z + x * y)
    cosy_cosp = 1 - 2 * (y * y + z * z)
    yaw = math.atan2(siny_cosp, cosy_cosp)
    
    # Range limiting
    # Limit pitch to (-π/2 + epsilon, π/2 - epsilon)
    pitch_limit = math.pi/2 - epsilon
    if pitch > pitch_limit:
        pitch = pitch_limit
    elif pitch < -pitch_limit:
        pitch = -pitch_limit
    
    def normalize_angle(angle):
        """Normalize angle to (-π, π) range"""
        while angle > math.pi:
            angle -= 2 * math.pi
        while angle <= -math.pi:
            angle += 2 * math.pi
        return angle
    
    roll = normalize_angle(roll)
    yaw = normalize_angle(yaw)

    # Limit roll and yaw to (-π + epsilon, π - epsilon)
    roll_yaw_limit = math.pi - epsilon
    
    if roll > roll_yaw_limit:
        roll = roll_yaw_limit
    elif roll < -roll_yaw_limit:
        roll = -roll_yaw_limit
    
    if yaw > roll_yaw_limit:
        yaw = roll_yaw_limit
    elif yaw < -roll_yaw_limit:
        yaw = -roll_yaw_limit
    
    return roll, pitch, yaw
    