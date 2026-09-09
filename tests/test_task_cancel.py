import threading
import pytest
from unittest.mock import MagicMock, patch
from app.routes import _check_cancel, CancelledError, _cancel_flags


class TestCheckCancel:
    def test_does_nothing_when_event_is_none(self):
        """_check_cancel with no event should not raise."""
        mock_tm = MagicMock()
        _check_cancel(None, "task_1", mock_tm)  # should not raise
        mock_tm.update.assert_not_called()

    def test_does_nothing_when_event_not_set(self):
        """_check_cancel with a clear event should not raise."""
        event = threading.Event()
        mock_tm = MagicMock()
        _check_cancel(event, "task_1", mock_tm)  # should not raise
        mock_tm.update.assert_not_called()

    def test_raises_when_event_is_set(self):
        """_check_cancel with a set event should raise CancelledError and reset status."""
        event = threading.Event()
        event.set()
        mock_tm = MagicMock()
        _cancel_flags["task_x"] = event

        with pytest.raises(CancelledError):
            _check_cancel(event, "task_x", mock_tm)

        mock_tm.update.assert_called_once_with("task_x", {'status': -1})
        assert "task_x" not in _cancel_flags

    def test_cleans_up_flag_on_cancel(self):
        """After CancelledError, the task_id should be removed from _cancel_flags."""
        event = threading.Event()
        event.set()
        mock_tm = MagicMock()
        _cancel_flags["task_cleanup"] = event

        with pytest.raises(CancelledError):
            _check_cancel(event, "task_cleanup", mock_tm)

        assert "task_cleanup" not in _cancel_flags


class TestCancelEndpoint:
    @pytest.fixture
    def client(self):
        from app import app as flask_app
        flask_app.config['TESTING'] = True
        with flask_app.test_client() as client:
            yield client

    def test_cancel_returns_404_for_missing_task(self, client):
        with patch('app.routes.TaskManager') as MockTM:
            MockTM.return_value.get.return_value = None
            res = client.post('/task/nonexistent/cancel')
        assert res.status_code == 404

    def test_cancel_returns_400_when_task_not_cancellable(self, client):
        with patch('app.routes.TaskManager') as MockTM:
            MockTM.return_value.get.return_value = {'status': 2, 'id': 'task_done'}
            res = client.post('/task/task_done/cancel')
        assert res.status_code == 400

    def test_cancel_sets_flag_and_resets_status(self, client):
        event = threading.Event()
        _cancel_flags["task_pending"] = event

        with patch('app.routes.TaskManager') as MockTM:
            MockTM.return_value.get.return_value = {'status': 1, 'id': 'task_pending'}
            res = client.post('/task/task_pending/cancel')
            MockTM.return_value.update.assert_called_once_with('task_pending', {'status': -1})

        assert event.is_set()
        assert res.status_code == 200

    def test_cancel_waiting_task_no_flag(self, client):
        """A waiting task (status=0) with no running thread should still reset to -1."""
        with patch('app.routes.TaskManager') as MockTM:
            MockTM.return_value.get.return_value = {'status': 0, 'id': 'task_waiting'}
            res = client.post('/task/task_waiting/cancel')
            MockTM.return_value.update.assert_called_once_with('task_waiting', {'status': -1})

        assert res.status_code == 200
