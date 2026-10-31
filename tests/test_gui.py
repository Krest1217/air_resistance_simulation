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
        self.assertGreater(len(app.chart.find_all()), 30)
        app.progress.set(0)
        app.draw()
        self.assertEqual(app.selected()[0].t, 0)
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
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'result.csv'
            with patch('main.filedialog.asksaveasfilename', return_value=str(path)):
                app.export()
            with path.open(encoding='utf-8-sig', newline='') as f:
                rows = list(csv.reader(f))
            self.assertEqual(len(rows), len(app.data)+3)
            self.assertEqual(float(rows[-1][2]), 0)
            self.assertGreater(float(rows[-1][-1]), 0)
        app.fields['mass'].set('0')
        with patch('main.messagebox.showerror') as dialog:
            app.run()
            dialog.assert_called_once()
        self.assertEqual(errors, [])


if __name__ == '__main__':
    unittest.main()
