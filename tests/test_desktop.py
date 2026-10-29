"""Desktop lifecycle checks without opening windows or launching real servers."""
import threading
from types import SimpleNamespace

import start
from desktop import DesktopApp


def test_desktop_stop_signal_shuts_down_all_owned_components(tmp_path, monkeypatch):
    stop = tmp_path / "stop"
    stop.touch()
    children = []

    class Child:
        stopped = False

        def __init__(self, *args, **kwargs):
            children.append(self)
            self.pid = len(children)

        def poll(self):
            return 0 if self.stopped else None

        def terminate(self):
            self.stopped = True

        def wait(self, timeout):
            return 0

    monkeypatch.setattr(start, "ROOT", tmp_path)
    monkeypatch.setattr(start.subprocess, "Popen", Child)
    def stop_tree(command, **kwargs):
        children[int(command[2]) - 1].terminate()
    monkeypatch.setattr(start.subprocess, "run", stop_tree)
    monkeypatch.setattr("sys.argv", ["start.py", "--stop-file", str(stop)])
    monkeypatch.setenv("GYMPULSE_START_LOCK", str(tmp_path / "isolated/start.lock"))
    monkeypatch.chdir(tmp_path)
    assert start.main() == 0
    assert len(children) == 3
    assert all(child.stopped for child in children)
    assert (tmp_path / "isolated").is_dir()


def test_desktop_waits_for_startup_worker_before_closing(tmp_path):
    closed = []
    app = DesktopApp.__new__(DesktopApp)
    app.closing = False
    app.worker_done = threading.Event()
    app.process = None
    app.log = None
    app.stop_path = tmp_path / "stop"
    widget = SimpleNamespace(config=lambda **kwargs: None)
    app.status = app.open_button = app.close_button = widget
    app.window = SimpleNamespace(destroy=lambda: closed.append(True), after=lambda *args: None)
    app.close()
    app.tick()
    assert app.stop_path.exists() and not closed
    app.worker_done.set()
    app.tick()
    assert closed == [True]
    assert not app.stop_path.exists()
