"""Executes fortune_extension.ipynb with OFFLINE = True: every cell must run and every assert hold.

    pip install nbclient nbformat ipykernel      # once
    python -m unittest test_notebook             # from this folder
"""

import unittest
from pathlib import Path

try:
    import nbformat
    from nbclient import NotebookClient
except ImportError:  # optional dependency
    nbformat = None

HERE = Path(__file__).resolve().parent


@unittest.skipIf(nbformat is None, "pip install nbclient nbformat ipykernel to run the notebook test")
class CompanionNotebook(unittest.TestCase):
    def test_runs_offline_end_to_end(self):
        nb = nbformat.read(HERE / "fortune_extension.ipynb", as_version=4)
        source = "".join(nb.cells[4].source)
        self.assertIn("OFFLINE = True", source, "commit the companion with OFFLINE = True")
        NotebookClient(nb, kernel_name="python3", timeout=120,
                       resources={"metadata": {"path": str(HERE)}}).execute()
        outputs = [o for c in nb.cells if c.cell_type == "code" for o in c.outputs]
        self.assertFalse([o for o in outputs if o.output_type == "error"])
        text = "".join(o.get("text", "") for o in outputs)
        for marker in ("baseline checks passed", "router checks passed", "reflection loop checks passed"):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
