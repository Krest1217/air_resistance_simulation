import math
import unittest
from physics import Parameters, simulate, vacuum, vacuum_time, drag_factor, terminal_speed, terminal_reached_time, Point


class PhysicsTests(unittest.TestCase):
    def test_vacuum_matches_analytic_and_conserves_energy(self):
        p = Parameters()
        points = simulate(p, drag=False)
        expected = vacuum(p, vacuum_time(p))
        self.assertAlmostEqual(points[-1].t, expected.t, places=9)
        self.assertAlmostEqual(points[-1].x, expected.x, places=8)
        e0 = points[0].energy(p.mass)
        self.assertTrue(all(abs(q.energy(p.mass)-e0) < 1e-7 for q in points))

    def test_shapes_land_and_lose_energy(self):
        for shape in ('sphere', 'cube', 'streamlined'):
            with self.subTest(shape=shape):
                p = Parameters(shape=shape)
                points = simulate(p)
                energies = [q.energy(p.mass) for q in points]
                self.assertEqual(points[-1].y, 0)
                self.assertGreater(points[-1].t, 0)
                self.assertTrue(all(q.y >= 0 for q in points))
                self.assertTrue(all(b <= a+1e-8 for a, b in zip(energies, energies[1:])))
                self.assertLess(energies[-1], energies[0])
                self.assertLess(points[-1].x, vacuum(p, vacuum_time(p)).x)

    def test_step_convergence(self):
        p = Parameters(speed=80, mass=0.02)
        a = simulate(p, max_step=0.01)[-1]
        b = simulate(p, max_step=0.005)[-1]
        self.assertLess(abs(a.x-b.x), 0.001)
        self.assertLess(abs(a.t-b.t), 0.001)

    def test_zero_speed_and_ground(self):
        self.assertEqual(len(simulate(Parameters(speed=0, height=0))), 1)
        self.assertEqual(len(simulate(Parameters(height=0, angle=-45))), 1)
        self.assertGreater(simulate(Parameters(height=0))[-1].t, 0)
        points = simulate(Parameters(speed=0, height=5))
        self.assertEqual(points[-1].x, 0)
        self.assertEqual(points[-1].y, 0)
        for shape in ('sphere', 'cube', 'streamlined'):
            self.assertTrue(math.isfinite(drag_factor(Parameters(shape=shape), 0)))

    def test_geometry(self):
        area, length = Parameters(shape='sphere', size=0.1).geometry
        self.assertAlmostEqual(area, math.pi * 0.05**2)
        self.assertEqual(length, 0.1)
        self.assertEqual(Parameters(shape='cube', size=2).geometry, (4, 2))
        area, length = Parameters(shape='streamlined', size=4).geometry
        self.assertAlmostEqual(area, math.pi/4)
        self.assertEqual(length, 1)

    def test_terminal_force_balance(self):
        from physics import G
        for shape in ('sphere', 'cube', 'streamlined'):
            for mass, size in ((0.2, 0.1), (0.0001, 0.01)):
                p = Parameters(shape=shape, mass=mass, size=size)
                v = terminal_speed(p)
                self.assertGreater(v, 0)
                self.assertAlmostEqual(drag_factor(p, v)*v, p.mass*G, places=9)

    def test_terminal_reached_and_not_reached(self):
        p = Parameters(speed=0, height=1000)
        points = simulate(p)
        v = terminal_speed(p)
        reached = terminal_reached_time(points, v)
        self.assertIsNotNone(reached)
        self.assertGreater(reached, 0)
        self.assertLess(reached, points[-1].t)
        self.assertIsNone(terminal_reached_time(simulate(Parameters()), v))
        self.assertIsNone(terminal_reached_time([Point(0, 0, 0, 0, -v)], v))
        self.assertIsNone(terminal_reached_time([Point(0, 0, 10, 0, v)], v))
        self.assertIsNone(terminal_reached_time([Point(0, 0, 10, v, -v)], v))
        self.assertIsNone(terminal_reached_time([Point(0, 0, 10, 0, -2*v)], v))
        self.assertEqual(terminal_reached_time([Point(0, 0, 10, 0, -v)], v), 0)

    def test_invalid_inputs(self):
        for kw in ({'mass': 0}, {'size': -1}, {'speed': float('nan')},
                   {'height': float('inf')}, {'angle': 91}, {'shape': 'unknown'}):
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                simulate(Parameters(**kw))


if __name__ == '__main__':
    unittest.main()
