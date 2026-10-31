"""2D projectile model. SI units, Python standard library only."""
from dataclasses import dataclass
import math

RHO = 101325 / (287.05 * 298)
MU = 1.837e-5
G = 9.80665


@dataclass(frozen=True)
class Parameters:
    shape: str = 'sphere'
    size: float = 0.1
    mass: float = 0.2
    speed: float = 25
    angle: float = 45
    height: float = 1.5

    def validate(self):
        if self.shape not in ('sphere', 'cube', 'streamlined'):
            raise ValueError('지원하지 않는 형상입니다.')
        bounds = {'size': (0.0001, 10), 'mass': (0.0001, 10000),
                  'speed': (0, 100), 'angle': (-90, 90), 'height': (0, 10000)}
        for key, (low, high) in bounds.items():
            value = getattr(self, key)
            if not math.isfinite(value) or not low <= value <= high:
                raise ValueError(f'{key}: {low} ~ {high} 범위의 유한한 값을 입력하세요.')

    @property
    def geometry(self):
        if self.shape == 'sphere':
            return math.pi * (self.size / 2)**2, self.size
        if self.shape == 'cube':
            return self.size**2, self.size
        diameter = self.size / 4
        return math.pi * (diameter / 2)**2, diameter


def drag_factor(p, speed):
    """F_drag/speed; finite at zero speed (Stokes limit)."""
    area, length = p.geometry
    re = RHO * speed * length / MU
    if p.shape == 'sphere':
        if re < 1000:
            return 12 * MU * area / length * (1 + 0.15 * re**0.687)
        return 0.5 * RHO * area * 0.44 * speed
    cd = 1.05 if p.shape == 'cube' else 0.10
    return 12 * MU * area / length + 0.5 * RHO * area * cd * speed


@dataclass(frozen=True)
class Point:
    t: float
    x: float
    y: float
    vx: float
    vy: float

    def energy(self, mass):
        return mass * (0.5 * (self.vx**2 + self.vy**2) + G * self.y)


def vacuum(p, t):
    angle = math.radians(p.angle)
    vx, vy = p.speed * math.cos(angle), p.speed * math.sin(angle)
    return Point(t, vx*t, max(0, p.height + vy*t - G*t*t/2), vx, vy-G*t)


def vacuum_time(p):
    vy = p.speed * math.sin(math.radians(p.angle))
    return (vy + math.sqrt(vy*vy + 2*G*p.height)) / G


def simulate(p, drag=True, max_step=0.02):
    p.validate()
    if not math.isfinite(max_step) or max_step <= 0:
        raise ValueError('시간 간격은 양수여야 합니다.')
    angle = math.radians(p.angle)
    state = (0., p.height, p.speed*math.cos(angle), p.speed*math.sin(angle))
    result = [Point(0., *state)]
    if p.height == 0 and state[3] <= 0:
        return result

    def derivative(s):
        _, _, vx, vy = s
        factor = drag_factor(p, math.hypot(vx, vy)) / p.mass if drag else 0
        return (vx, vy, -factor*vx, -G-factor*vy)

    def step(s, dt):
        a = derivative(s)
        b = derivative(tuple(v+dt*k/2 for v, k in zip(s, a)))
        c = derivative(tuple(v+dt*k/2 for v, k in zip(s, b)))
        d = derivative(tuple(v+dt*k for v, k in zip(s, c)))
        return tuple(v+dt*(a0+2*b0+2*c0+d0)/6
                     for v, a0, b0, c0, d0 in zip(s, a, b, c, d))

    t = 0.
    for _ in range(300000):
        factor = drag_factor(p, math.hypot(state[2], state[3])) if drag else 0
        dt = min(max_step, 0.15*p.mass/factor) if factor else max_step
        nxt = step(state, dt)
        if nxt[1] <= 0:
            low, high = 0., dt
            for _ in range(35):
                mid = (low+high)/2
                if step(state, mid)[1] > 0:
                    low = mid
                else:
                    high = mid
            dt = (low+high)/2
            nxt = step(state, dt)
            result.append(Point(t+dt, nxt[0], 0., nxt[2], nxt[3]))
            return result
        t += dt
        state = nxt
        result.append(Point(t, *state))
    raise ValueError('계산 한도를 초과했습니다. 크기·질량·높이 조합을 완화해 주세요.')
