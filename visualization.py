import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from multiprocessing import Queue
import time
from collections import defaultdict


class LogVisualizer:
    def __init__(self, analysis_queue, alert_queue):
        self.analysis_queue = analysis_queue
        self.alert_queue = alert_queue
        self.device_data = defaultdict(lambda: {
            "timestamps": [],
            "error_ratios": [],
            "warn_ratios": [],
            "last_error": None,
            "alerts": []
        })

        plt.style.use('ggplot')
        self.fig, self.ax = plt.subplots(figsize=(10, 6))
        self.fig.canvas.manager.set_window_title('日志监控系统')

    def update_plot(self, frame):
        self.ax.clear()

        # 从队列获取分析结果
        while not self.analysis_queue.empty():
            data = self.analysis_queue.get()
            device_id = data["device_id"]
            self.device_data[device_id]["timestamps"].append(data["timestamp"])
            self.device_data[device_id]["error_ratios"].append(data["error_ratio"])
            self.device_data[device_id]["warn_ratios"].append(data["warn_ratio"])
            self.device_data[device_id]["last_error"] = data["last_error"]

        # 从队列获取告警
        while not self.alert_queue.empty():
            alert = self.alert_queue.get()
            self.device_data[alert["device_id"]]["alerts"].append(alert)
            print(f"收到告警: {alert}")

        # 绘制图表
        for device_id, data in self.device_data.items():
            if len(data["timestamps"]) > 0:
                recent_points = min(20, len(data["timestamps"]))
                timestamps = data["timestamps"][-recent_points:]
                error_ratios = data["error_ratios"][-recent_points:]
                warn_ratios = data["warn_ratios"][-recent_points:]

                self.ax.plot(timestamps, error_ratios, label=f"{device_id} ERROR比例", marker='o')
                self.ax.plot(timestamps, warn_ratios, label=f"{device_id} WARN比例", marker='x')

                if data["last_error"]:
                    self.ax.text(0.02, 0.95 - 0.05 * list(self.device_data.keys()).index(device_id),
                                 f"{device_id} 最后错误: {data['last_error']['message']}",
                                 transform=self.ax.transAxes)

                if data["alerts"]:
                    self.ax.text(0.02, 0.85 - 0.05 * list(self.device_data.keys()).index(device_id),
                                 f"告警: {data['alerts'][-1]['message']}",
                                 color='red', transform=self.ax.transAxes)

        self.ax.set_title('日志级别比例监控')
        self.ax.set_xlabel('时间')
        self.ax.set_ylabel('比例')
        self.ax.legend()
        self.ax.set_ylim(0, 1)
        plt.xticks(rotation=45)
        self.fig.tight_layout()


if __name__ == "__main__":
    # 注意：这里的队列要和 log_analyzer.py 使用相同的队列对象
    # 实际运行时，需要确保队列是在主进程中创建的
    analysis_queue = Queue()
    alert_queue = Queue()

    visualizer = LogVisualizer(analysis_queue, alert_queue)
    ani = FuncAnimation(visualizer.fig, visualizer.update_plot, interval=1000)
    plt.show()