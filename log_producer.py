import time
import random
from datetime import datetime
from multiprocessing import Process, Queue

DEVICE_IDS = ["device1", "device2", "device3"]


def generate_log(device_id):
    levels = ["INFO", "WARN", "ERROR"]
    messages = {
        "INFO": ["系统状态正常", "用户登录成功"],
        "WARN": ["内存使用率过高", "磁盘空间不足"],
        "ERROR": ["系统崩溃", "数据库连接失败"]
    }
    level = random.choices(levels, weights=[70, 20, 10])[0]
    return {
        "device_id": device_id,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "log_level": level,
        "message": random.choice(messages[level])
    }


def log_producer(device_id, queue):
    while True:
        log = generate_log(device_id)
        queue.put(log)
        print(f"[{device_id}] 生成日志: {log}")
        time.sleep(0.1)  # 100ms


if __name__ == "__main__":
    log_queue = Queue()  # 共享队列
    producers = []

    # 启动多个日志采集进程
    for device_id in DEVICE_IDS:
        p = Process(target=log_producer, args=(device_id, log_queue))
        p.start()
        producers.append(p)

    # 阻塞主进程
    for p in producers:
        p.join()