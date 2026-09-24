"""
รันคำสั่งแล้วแสดงผลบนหน้าจอพร้อมกับเขียนลงไฟล์ log ไปด้วย (ใช้ใน train.bat)

รัน: python run_logged.py <log_file> <command> [args...]
คืน exit code เดียวกับคำสั่งที่รัน
"""
import subprocess
import sys

log_path, *cmd = sys.argv[1:]
with open(log_path, "ab") as log:
    # อ่านเป็น byte แล้วส่งต่อตรง ๆ ไม่ decode เพื่อไม่ให้ภาษาไทยเพี้ยนระหว่างทาง
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in iter(proc.stdout.readline, b""):
        sys.stdout.buffer.write(line)
        sys.stdout.buffer.flush()
        log.write(line)
        log.flush()
sys.exit(proc.wait())
