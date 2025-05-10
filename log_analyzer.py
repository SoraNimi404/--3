from multiprocessing import Process, Queue
from collections import deque
import time

N = 100  # 维护最近N条日志
T = 5  # 每T秒发布分析结果
S = 10  # S秒内ERROR超50%则告警


def log_analyzer(log_queue, analysis_queue, alert_queue):
    device_logs = {}  # {device_id: deque(maxlen=N)}

    while True:
        # 从队列获取日志
        if not log_queue.empty():
            log = log_queue.get()
            device_id = log["device_id"]

            if device_id not in device_logs:
                device_logs[device_id] = deque(maxlen=N)
            device_logs[device_id].append(log)

        # 每T秒分析一次
        time.sleep(T)
        for device_id, logs in device_logs.items():
            if not logs:
                continue

            error_count = sum(1 for log in logs if log["log_level"] == "ERROR")
            warn_count = sum(1 for log in logs if log["log_level"] == "WARN")
            total = len(logs)

            error_ratio = error_count / total
            warn_ratio = warn_count / total

            last_error = next((log for log in reversed(logs) if log["log_level"] == "ERROR"), None)

            # 发送分析结果
            analysis_queue.put({
                "device_id": device_id,
                "error_ratio": error_ratio,
                "warn_ratio": warn_ratio,
                "last_error": last_error,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            })

            # 检查是否需要告警
            recent_logs = list(logs)[-int(S * 10):]  # 假设每秒10条日志
            if len(recent_logs) > 0 and (
                    sum(1 for log in recent_logs if log["log_level"] == "ERROR") / len(recent_logs)) > 0.5:
                alert_queue.put({
                    "device_id": device_id,
                    "message": "ERROR比例超过50%!",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                })


if __name__ == "__main__":
    log_queue = Queue()  # 日志队列
    analysis_queue = Queue()  # 分析结果队列
    alert_queue = Queue()  # 告警队列

    analyzer = Process(target=log_analyzer, args=(log_queue, analysis_queue, alert_queue))
    analyzer.start()

    # 阻塞主进程
    analyzer.join()