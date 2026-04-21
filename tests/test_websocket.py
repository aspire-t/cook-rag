"""
测试 WebSocket 跟做模式 (Task #30)

Sprint 10
TDD: 测试 WebSocket 连接、步骤推送、倒计时功能
"""

import pytest
from pathlib import Path


class TestWebSocketModule:
    """测试 WebSocket 模块"""

    @pytest.fixture
    def websocket_file(self) -> str:
        """读取 app/api/v1/websocket.py"""
        websocket_path = Path(__file__).parent.parent / "app" / "api" / "v1" / "websocket.py"
        if websocket_path.exists():
            with open(websocket_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_websocket_file_exists(self):
        """测试 WebSocket 文件存在"""
        websocket_path = Path(__file__).parent.parent / "app" / "api" / "v1" / "websocket.py"
        assert websocket_path.exists(), "app/api/v1/websocket.py 应该存在"

    def test_connection_manager_class(self, websocket_file):
        """测试 ConnectionManager 类"""
        assert "class ConnectionManager" in websocket_file, "应该有 ConnectionManager 类"
        assert "active_connections" in websocket_file, "应该有活跃连接管理"
        assert "cooking_sessions" in websocket_file, "应该有跟做会话管理"

    def test_connect_method(self, websocket_file):
        """测试连接方法"""
        assert "async def connect" in websocket_file, "应该有 connect 方法"
        assert "websocket.accept" in websocket_file or "await websocket.accept" in websocket_file, "应该接受 WebSocket 连接"

    def test_disconnect_method(self, websocket_file):
        """测试断开方法"""
        assert "def disconnect" in websocket_file, "应该有 disconnect 方法"

    def test_broadcast_method(self, websocket_file):
        """测试广播方法"""
        assert "async def broadcast_to_recipe" in websocket_file, "应该有 broadcast_to_recipe 方法"

    def test_cooking_session_management(self, websocket_file):
        """测试跟做会话管理"""
        assert "create_cooking_session" in websocket_file, "应该有创建会话方法"
        assert "get_cooking_session" in websocket_file, "应该有获取会话方法"
        assert "update_cooking_session" in websocket_file, "应该有更新会话方法"


class TestWebSocketOperations:
    """测试 WebSocket 操作"""

    @pytest.fixture
    def websocket_file(self) -> str:
        """读取 app/api/v1/websocket.py"""
        websocket_path = Path(__file__).parent.parent / "app" / "api" / "v1" / "websocket.py"
        if websocket_path.exists():
            with open(websocket_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_start_operation(self, websocket_file):
        """测试开始跟做操作"""
        assert '"start"' in websocket_file or "'start'" in websocket_file, "应该支持 start 操作"
        assert "current_step" in websocket_file, "应该有当前步骤跟踪"

    def test_next_operation(self, websocket_file):
        """测试下一步操作"""
        assert '"next"' in websocket_file or "'next'" in websocket_file, "应该支持 next 操作"

    def test_prev_operation(self, websocket_file):
        """测试上一步操作"""
        assert '"prev"' in websocket_file or "'prev'" in websocket_file, "应该支持 prev 操作"

    def test_pause_operation(self, websocket_file):
        """测试暂停操作"""
        assert '"pause"' in websocket_file or "'pause'" in websocket_file, "应该支持 pause 操作"

    def test_resume_operation(self, websocket_file):
        """测试继续操作"""
        assert '"resume"' in websocket_file or "'resume'" in websocket_file, "应该支持 resume 操作"

    def test_timer_operations(self, websocket_file):
        """测试计时器操作"""
        assert '"timer_start"' in websocket_file or "'timer_start'" in websocket_file, "应该支持 timer_start 操作"
        assert '"timer_stop"' in websocket_file or "'timer_stop'" in websocket_file, "应该支持 timer_stop 操作"

    def test_status_operation(self, websocket_file):
        """测试状态查询操作"""
        assert '"status"' in websocket_file or "'status'" in websocket_file, "应该支持 status 操作"

    def test_complete_operation(self, websocket_file):
        """测试完成操作"""
        assert '"complete"' in websocket_file or "'complete'" in websocket_file, "应该支持 complete 操作"


class TestCountdownTimer:
    """测试倒计时功能"""

    @pytest.fixture
    def websocket_file(self) -> str:
        """读取 app/api/v1/websocket.py"""
        websocket_path = Path(__file__).parent.parent / "app" / "api" / "v1" / "websocket.py"
        if websocket_path.exists():
            with open(websocket_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_countdown_function_exists(self, websocket_file):
        """测试倒计时函数存在"""
        assert "async def countdown_timer" in websocket_file, "应该有 countdown_timer 函数"

    def test_timer_update_broadcast(self, websocket_file):
        """测试计时器更新广播"""
        assert "timer_update" in websocket_file, "应该广播 timer_update 消息"
        assert "remaining_seconds" in websocket_file, "应该发送剩余秒数"

    def test_timer_complete_event(self, websocket_file):
        """测试计时完成事件"""
        assert "timer_complete" in websocket_file, "应该发送 timer_complete 消息"

    def test_time_formatting(self, websocket_file):
        """测试时间格式化"""
        assert "format_time" in websocket_file, "应该有 format_time 函数"
        assert "MM:SS" in websocket_file or "minutes" in websocket_file, "应该格式化为 MM:SS 格式"


class TestStepPush:
    """测试步骤推送"""

    @pytest.fixture
    def websocket_file(self) -> str:
        """读取 app/api/v1/websocket.py"""
        websocket_path = Path(__file__).parent.parent / "app" / "api" / "v1" / "websocket.py"
        if websocket_path.exists():
            with open(websocket_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_get_recipe_steps_function(self, websocket_file):
        """测试获取菜谱步骤函数"""
        assert "async def get_recipe_steps" in websocket_file, "应该有 get_recipe_steps 函数"

    def test_step_update_broadcast(self, websocket_file):
        """测试步骤更新广播"""
        assert "step_update" in websocket_file, "应该广播 step_update 消息"

    def test_step_data_structure(self, websocket_file):
        """测试步骤数据结构"""
        assert "step_number" in websocket_file, "应该有 step_number"
        assert "description" in websocket_file, "应该有 description"
        assert "duration_seconds" in websocket_file, "应该有 duration_seconds"

    def test_progress_tracking(self, websocket_file):
        """测试进度跟踪"""
        assert "progress" in websocket_file, "应该有进度跟踪"
        assert "completed_steps" in websocket_file, "应该有已完成步骤列表"


class TestWebSocketEndpoint:
    """测试 WebSocket 端点"""

    @pytest.fixture
    def websocket_file(self) -> str:
        """读取 app/api/v1/websocket.py"""
        websocket_path = Path(__file__).parent.parent / "app" / "api" / "v1" / "websocket.py"
        if websocket_path.exists():
            with open(websocket_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_websocket_endpoint_exists(self, websocket_file):
        """测试 WebSocket 端点存在"""
        assert "async def websocket_endpoint" in websocket_file, "应该有 websocket_endpoint 函数"

    def test_websocket_parameter(self, websocket_file):
        """测试 WebSocket 参数"""
        assert "WebSocket" in websocket_file, "应该有 WebSocket 类型"
        assert "recipe_id" in websocket_file, "应该有 recipe_id 参数"

    def test_recipe_validation(self, websocket_file):
        """测试菜谱验证"""
        assert "Recipe" in websocket_file, "应该验证菜谱存在"
        assert "scalar_one_or_none" in websocket_file or "4004" in websocket_file, "应该处理菜谱不存在情况"

    def test_initial_message(self, websocket_file):
        """测试初始消息"""
        assert "connected" in websocket_file, "应该发送 connected 消息"
        assert "total_steps" in websocket_file, "应该发送总步骤数"

    def test_disconnect_handling(self, websocket_file):
        """测试断开处理"""
        assert "WebSocketDisconnect" in websocket_file, "应该处理 WebSocketDisconnect 异常"
        assert "websocket.close" in websocket_file, "应该关闭连接"


class TestMessageTypes:
    """测试消息类型"""

    @pytest.fixture
    def websocket_file(self) -> str:
        """读取 app/api/v1/websocket.py"""
        websocket_path = Path(__file__).parent.parent / "app" / "api" / "v1" / "websocket.py"
        if websocket_path.exists():
            with open(websocket_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_connected_message(self, websocket_file):
        """测试 connected 消息"""
        assert '"connected"' in websocket_file or "'connected'" in websocket_file, "应该有 connected 消息"

    def test_step_update_message(self, websocket_file):
        """测试 step_update 消息"""
        assert '"step_update"' in websocket_file or "'step_update'" in websocket_file, "应该有 step_update 消息"

    def test_pause_message(self, websocket_file):
        """测试 pause 消息"""
        assert '"pause"' in websocket_file or "'pause'" in websocket_file, "应该有 pause 消息"

    def test_resume_message(self, websocket_file):
        """测试 resume 消息"""
        assert '"resume"' in websocket_file or "'resume'" in websocket_file, "应该有 resume 消息"

    def test_timer_messages(self, websocket_file):
        """测试计时器消息"""
        assert '"timer_update"' in websocket_file or "'timer_update'" in websocket_file, "应该有 timer_update 消息"
        assert '"timer_complete"' in websocket_file or "'timer_complete'" in websocket_file, "应该有 timer_complete 消息"

    def test_complete_message(self, websocket_file):
        """测试 complete 消息"""
        assert '"complete"' in websocket_file or "'complete'" in websocket_file, "应该有 complete 消息"


class TestIntegration:
    """测试集成"""

    @pytest.fixture
    def main_file(self) -> str:
        """读取 app/main.py"""
        main_path = Path(__file__).parent.parent / "app" / "main.py"
        if main_path.exists():
            with open(main_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def test_websocket_endpoint_registered(self, main_file):
        """测试 WebSocket 端点注册"""
        assert "websocket" in main_file.lower() or "WebSocket" in main_file, "应该导入 websocket 模块"
        assert "@app.websocket" in main_file, "应该注册 WebSocket 端点"
        assert "/ws/recipes/" in main_file or "recipe_id" in main_file, "应该有菜谱 WebSocket 路径"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
