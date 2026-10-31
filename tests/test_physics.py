import math
import unittest
from physics import Parameters, simulate, vacuum, vacuum_time, drag_factor


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

    def test_invalid_inputs(self):
        for kw in ({'mass': 0}, {'size': -1}, {'speed': float('nan')},
                   {'height': float('inf')}, {'angle': 91}, {'shape': 'unknown'}):
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                simulate(Parameters(**kw))


if __name__ == '__main__':
    unittest.main()
