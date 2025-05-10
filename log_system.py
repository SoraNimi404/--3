import json
import random
import time
import threading
from queue import Queue
from collections import deque
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# 全局配置
CONFIG = {
    'device_ids': ['device1', 'device2', 'device3'],
    'log_levels': ['INFO', 'WARN', 'ERROR'],
    'sample_messages': {
        'INFO': ['系统状态正常', '操作已完成', '服务启动成功'],
        'WARN': ['内存使用率过高', '磁盘空间不足', '网络延迟增加'],
        'ERROR': ['服务崩溃', '连接超时', '硬件故障']
    },
    'analysis_window': 20,  # 分析的日志窗口大小N
    'analysis_interval': 5,  # 分析间隔T秒
    'alert_threshold': 0.5,  # 告警阈值(ERROR占比)
    'alert_window': 10,  # 告警检测窗口S秒
    'log_generation_interval': 0.1  # 日志生成间隔(秒)
}

# 全局消息队列
log_queue = Queue()
analysis_queue = Queue()
alert_queue = Queue()


class LogGenerator:
    """日志生成器，模拟多个设备生成日志"""

    def __init__(self, device_id):
        self.device_id = device_id

    def generate_log(self):
        """生成一条日志"""
        log_level = random.choices(
            CONFIG['log_levels'],
            weights=[0.7, 0.2, 0.1],  # INFO:70%, WARN:20%, ERROR:10%
            k=1
        )[0]

        log = {
            "device_id": self.device_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "log_level": log_level,
            "message": random.choice(CONFIG['sample_messages'][log_level])
        }
        return log

    def publish_log(self):
        """发布日志到消息队列"""
        while True:
            log = self.generate_log()
            log_queue.put(log)
            print(f"Device {self.device_id} sent log: {log}")
            time.sleep(CONFIG['log_generation_interval'])

    def start(self):
        """启动日志生成"""
        thread = threading.Thread(target=self.publish_log)
        thread.daemon = True
        thread.start()


class LogAnalyzer:
    """日志分析器，检测异常并生成统计"""

    def __init__(self):
        # 设备日志缓存 {device_id: deque}
        self.logs_cache = {device_id: deque(maxlen=CONFIG['analysis_window'])
                           for device_id in CONFIG['device_ids']}

        # 设备状态 {device_id: {'last_error': {...}, 'alerts': []}}
        self.device_status = {device_id: {'last_error': None, 'alerts': []}
                              for device_id in CONFIG['device_ids']}

        # 告警时间窗口 {device_id: deque}
        self.alert_windows = {device_id: deque(maxlen=CONFIG['alert_window'])
                              for device_id in CONFIG['device_ids']}

    def analyze_logs(self):
        """分析日志并发布结果"""
        for device_id in CONFIG['device_ids']:
            logs = list(self.logs_cache[device_id])
            if not logs:
                continue

            # 计算各级别日志占比
            total = len(logs)
            error_count = sum(1 for log in logs if log['log_level'] == 'ERROR')
            warn_count = sum(1 for log in logs if log['log_level'] == 'WARN')

            error_ratio = error_count / total
            warn_ratio = warn_count / total

            # 更新最后ERROR事件
            error_logs = [log for log in logs if log['log_level'] == 'ERROR']
            if error_logs:
                self.device_status[device_id]['last_error'] = error_logs[-1]

            # 检查是否需要告警
            self.alert_windows[device_id].append(error_ratio)
            if len(self.alert_windows[device_id]) == CONFIG['alert_window']:
                avg_error_ratio = sum(self.alert_windows[device_id]) / CONFIG['alert_window']
                if avg_error_ratio > CONFIG['alert_threshold']:
                    alert = {
                        "device_id": device_id,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "message": f"设备{device_id} ERROR比例超过50%",
                        "severity": "CRITICAL"
                    }
                    self.device_status[device_id]['alerts'].append(alert)
                    alert_queue.put(alert)
                    print(f"Alert generated: {alert}")
                    # 清空窗口避免重复告警
                    self.alert_windows[device_id].clear()

            # 发布分析结果
            analysis_result = {
                "device_id": device_id,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "error_ratio": error_ratio,
                "warn_ratio": warn_ratio,
                "last_error": self.device_status[device_id]['last_error'],
                "alert_count": len(self.device_status[device_id]['alerts'])
            }

            analysis_queue.put(analysis_result)

    def process_logs(self):
        """处理日志队列中的日志"""
        while True:
            try:
                log = log_queue.get_nowait()
                device_id = log['device_id']
                self.logs_cache[device_id].append(log)
            except:
                time.sleep(0.1)

    def start(self):
        """启动分析服务"""
        # 启动日志处理线程
        process_thread = threading.Thread(target=self.process_logs)
        process_thread.daemon = True
        process_thread.start()

        # 定时分析
        while True:
            time.sleep(CONFIG['analysis_interval'])
            self.analyze_logs()


class MonitoringDashboard:
    """监控仪表板，实时可视化日志分析结果"""

    def __init__(self):
        # 初始化数据存储
        self.analysis_data = {device_id: {'timestamps': [], 'error_ratios': [], 'warn_ratios': []}
                              for device_id in CONFIG['device_ids']}
        self.alerts = []

        # 初始化图表
        plt.style.use('ggplot')
        self.fig, self.axes = plt.subplots(nrows=2, ncols=len(CONFIG['device_ids']),
                                           figsize=(15, 10))
        self.fig.suptitle('分布式日志监控系统')

        # 启动UI更新线程
        self.update_thread = threading.Thread(target=self.update_ui)
        self.update_thread.daemon = True
        self.update_thread.start()

    def process_queues(self):
        """处理消息队列"""
        while True:
            # 处理分析结果队列
            try:
                result = analysis_queue.get_nowait()
                device_id = result['device_id']

                # 存储数据
                self.analysis_data[device_id]['timestamps'].append(result['timestamp'])
                self.analysis_data[device_id]['error_ratios'].append(result['error_ratio'])
                self.analysis_data[device_id]['warn_ratios'].append(result['warn_ratio'])

                # 限制数据量
                if len(self.analysis_data[device_id]['timestamps']) > 20:
                    self.analysis_data[device_id]['timestamps'].pop(0)
                    self.analysis_data[device_id]['error_ratios'].pop(0)
                    self.analysis_data[device_id]['warn_ratios'].pop(0)
            except:
                pass

            # 处理告警队列
            try:
                alert = alert_queue.get_nowait()
                self.alerts.append(alert)
                if len(self.alerts) > 5:
                    self.alerts.pop(0)
            except:
                pass

            time.sleep(0.1)

    def update_ui(self):
        """更新UI"""
        # 启动队列处理线程
        queue_thread = threading.Thread(target=self.process_queues)
        queue_thread.daemon = True
        queue_thread.start()

        # 启动动画
        ani = FuncAnimation(self.fig, self.update_plots, interval=1000)
        plt.show()

    def update_plots(self, frame):
        """更新图表"""
        for i, device_id in enumerate(CONFIG['device_ids']):
            # 清空当前轴
            self.axes[0, i].clear()
            self.axes[1, i].clear()

            # 绘制比率趋势图
            data = self.analysis_data[device_id]
            if data['timestamps']:
                self.axes[0, i].plot(data['timestamps'], data['error_ratios'],
                                     label='ERROR Ratio', color='red')
                self.axes[0, i].plot(data['timestamps'], data['warn_ratios'],
                                     label='WARN Ratio', color='orange')
                self.axes[0, i].set_title(f'Device {device_id} Log Ratios')
                self.axes[0, i].set_ylim(0, 1)
                self.axes[0, i].legend()
                self.axes[0, i].tick_params(axis='x', rotation=45)

            # 显示告警信息
            alert_text = "Recent Alerts:\n"
            for alert in self.alerts:
                if alert['device_id'] == device_id:
                    alert_text += f"{alert['timestamp']}: {alert['message']}\n"

            self.axes[1, i].text(0.1, 0.5, alert_text if alert_text != "Recent Alerts:\n"
            else "No recent alerts",
                                 fontsize=10)
            self.axes[1, i].axis('off')

        self.fig.tight_layout()

    def start(self):
        """启动监控服务"""
        self.update_ui()


def main():
    # 启动日志生成器
    generators = [LogGenerator(device_id) for device_id in CONFIG['device_ids']]
    for generator in generators:
        generator.start()

    # 启动分析器
    analyzer = LogAnalyzer()
    analyzer_thread = threading.Thread(target=analyzer.start)
    analyzer_thread.daemon = True
    analyzer_thread.start()

    # 启动监控面板
    dashboard = MonitoringDashboard()
    dashboard.start()

    # 保持主线程运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("系统关闭")


if __name__ == "__main__":
    main()