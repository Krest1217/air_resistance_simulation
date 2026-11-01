"""GUI smoke tests; skipped when no graphical display is available."""
import csv
import tempfile
import time
import tkinter as tk
from pathlib import Path
import unittest
from unittest.mock import patch
from main import App


class GuiTests(unittest.TestCase):
    def test_run_play_shapes_and_export(self):
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(str(exc))
        self.addCleanup(root.destroy)
        errors = []
        root.report_callback_exception = lambda *args: errors.append(args)
        app = App(root)

        def wait_ready():
            deadline = time.monotonic()+8
            while time.monotonic() < deadline:
                root.update()
                if app.data and str(app.run_button['state']) == 'normal':
                    return
                time.sleep(0.01)
            self.fail('Simulation did not complete')

        wait_ready()
        self.assertIn('도달하지 않음', app.speed_label['text'])
        self.assertIn('m/s', app.speed_label['text'])
        self.assertGreater(len(app.chart.find_all()), 30)
        app.progress.set(0)
        app.draw()
        self.assertEqual(app.selected()[0].t, 0)
        self.assertIn('현재속도 : 25.000 m/s', app.speed_label['text'])
        app.toggle()
        root.update()
        self.assertTrue(app.playing)
        app.toggle()
        self.assertFalse(app.playing)
        for shape in ('정육면체', '유선형체', '구'):
            app.shape.set(shape)
            app.shape_changed()
            app.run()
            wait_ready()
            self.assertEqual(app.data[-1].y, 0)
        app.progress.set(100)
        app.draw()
        q = app.data[-1]
        import math
        self.assertIn(f'현재속도 : {math.hypot(q.vx, q.vy):.3f} m/s', app.speed_label['text'])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'result.csv'
            with patch('main.filedialog.asksaveasfilename', return_value=str(path)):
                app.export()
            with path.open(encoding='utf-8-sig', newline='') as f:
                rows = list(csv.reader(f))
            self.assertEqual(len(rows), len(app.data)+3)
            self.assertEqual(float(rows[-1][2]), 0)
            self.assertGreater(float(rows[-1][-1]), 0)
        app.fields['height'].set('1000')
        app.fields['speed'].set('0')
        app.run()
        wait_ready()
        self.assertIn('초에 도달', app.speed_label['text'])
        app.fields['mass'].set('0')
        with patch('main.messagebox.showerror') as dialog:
            app.run()
            dialog.assert_called_once()
        for width, height in ((1180, 820), (1024, 720), (900, 480)):
            root.geometry(f'{width}x{height}')
            root.update()
            self.assertGreaterEqual(app.status.winfo_height(), app.status.winfo_reqheight())
            self.assertGreaterEqual(app.energy.winfo_height(), app.energy.winfo_reqheight())
            self.assertLessEqual(app.status.winfo_rooty()+app.status.winfo_height(),
                                 root.winfo_rooty()+root.winfo_height())
            app.viewport.yview_moveto(1)
            root.update()
            self.assertLessEqual(app.energy.winfo_rooty()+app.energy.winfo_height(),
                                 app.viewport.winfo_rooty()+app.viewport.winfo_height())
        # Reserve a visible gap below the status text, also with large fonts.
        app.status.configure(font=(app.font, 16))
        root.update()
        self.assertGreaterEqual(app.status.winfo_height(), app.status.winfo_reqheight())
        self.assertGreaterEqual(root.winfo_rooty()+root.winfo_height()
                                - app.status.winfo_rooty()-app.status.winfo_height(), 12)
        self.assertEqual(errors, [])


if __name__ == '__main__':
    unittest.main()
