import os
import time
import platform
import socket
import datetime
import psutil
from typing import Dict, List, Any, Tuple

# Pre-warm psutil cpu monitoring
psutil.cpu_percent(interval=None)
psutil.cpu_percent(interval=None, percpu=True)

def human_bytes(n: float) -> str:
    """Format bytes into readable string."""
    if n is None:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if abs(n) < 1024.0:
            return f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} EB"

def progress_bar(percent: float, length: int = 10) -> str:
    """Create a textual progress bar."""
    percent = max(0.0, min(100.0, percent))
    filled_len = int(round(length * percent / 100))
    bar = '█' * filled_len + '░' * (length - filled_len)
    return f"[{bar}] {percent:.1f}%"

def status_badge(percent: float, warn: float = 70.0, crit: float = 85.0) -> str:
    """Return status emoji based on threshold."""
    if percent >= crit:
        return "🔴"
    elif percent >= warn:
        return "🟡"
    return "🟢"

def format_timedelta(seconds: float) -> str:
    """Format seconds into readable days, hours, minutes."""
    td = datetime.timedelta(seconds=int(seconds))
    days = td.days
    hours, remainder = divmod(td.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days} дн.")
    if hours > 0 or days > 0:
        parts.append(f"{hours} год.")
    parts.append(f"{minutes} хв.")
    return " ".join(parts)

def get_cpu_model() -> str:
    """Read CPU model from /proc/cpuinfo or platform."""
    try:
        if os.path.exists('/proc/cpuinfo'):
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if 'model name' in line:
                        return line.split(':', 1)[1].strip()
    except Exception:
        pass
    return platform.processor() or "Невідомий CPU"

def get_public_ip() -> str:
    """Get public IP from external host or hostname."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1.0)
        # Doesn't actually connect, just finds routing interface IP
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return socket.gethostbyname(socket.gethostname())

def get_summary() -> str:
    """Generate high-level server overview dashboard."""
    # CPU
    cpu_pct = psutil.cpu_percent(interval=0.2)
    load_1, load_5, load_15 = psutil.getloadavg()
    cpu_count = psutil.cpu_count(logical=True) or 1
    
    # Memory
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    
    # Main Disk (/)
    root_disk = psutil.disk_usage('/')
    
    # Uptime
    boot_time = psutil.boot_time()
    uptime_sec = time.time() - boot_time
    
    # Network totals
    net = psutil.net_io_counters()
    
    # Process & users count
    procs_count = len(psutil.pids())
    users_count = len(psutil.users())
    hostname = socket.gethostname()
    
    text = (
        f"📊 <b>ОГЛЯД СЕРВЕРА</b>\n"
        f"<code>────────────────────────</code>\n"
        f"🖥 <b>Хост:</b> <code>{hostname}</code>\n"
        f"⏱ <b>Аптайм:</b> {format_timedelta(uptime_sec)}\n"
        f"👥 <b>Користувачів:</b> {users_count} онлайн | ⚙️ <b>Процесів:</b> {procs_count}\n\n"
        
        f"⚡ <b>CPU:</b> {status_badge(cpu_pct)}\n"
        f"<code>{progress_bar(cpu_pct)}</code>\n"
        f"• Load Average: <code>{load_1:.2f}, {load_5:.2f}, {load_15:.2f}</code> (ядер: {cpu_count})\n\n"
        
        f"🧠 <b>RAM (Пам'ять):</b> {status_badge(mem.percent)}\n"
        f"<code>{progress_bar(mem.percent)}</code>\n"
        f"• Використано: <b>{human_bytes(mem.used)}</b> / {human_bytes(mem.total)}\n"
        f"• Доступно: <b>{human_bytes(mem.available)}</b>\n\n"
        
        f"🔄 <b>SWAP:</b> {status_badge(swap.percent)}\n"
        f"<code>{progress_bar(swap.percent)}</code>\n"
        f"• Використано: <b>{human_bytes(swap.used)}</b> / {human_bytes(swap.total)}\n\n"
        
        f"💾 <b>Диск (/):</b> {status_badge(root_disk.percent)}\n"
        f"<code>{progress_bar(root_disk.percent)}</code>\n"
        f"• Зайнято: <b>{human_bytes(root_disk.used)}</b> / {human_bytes(root_disk.total)} (вільно {human_bytes(root_disk.free)})\n\n"
        
        f"🌐 <b>Мережа (Всього):</b>\n"
        f"• ⬇️ Отримано: <b>{human_bytes(net.bytes_recv)}</b>\n"
        f"• ⬆️ Передано: <b>{human_bytes(net.bytes_sent)}</b>\n"
        f"<code>────────────────────────</code>\n"
        f"🕒 <i>Оновлено: {datetime.datetime.now().strftime('%H:%M:%S (%d.%m.%Y)')}</i>"
    )
    return text

def get_cpu_details() -> str:
    """Detailed CPU metrics."""
    cpu_percents = psutil.cpu_percent(interval=0.3, percpu=True)
    avg_cpu = sum(cpu_percents) / len(cpu_percents) if cpu_percents else 0.0
    load_1, load_5, load_15 = psutil.getloadavg()
    cpu_model = get_cpu_model()
    logical_cores = psutil.cpu_count(logical=True)
    physical_cores = psutil.cpu_count(logical=False)
    
    freq = psutil.cpu_freq()
    freq_str = f"{freq.current:.0f} MHz" if freq and freq.current else "Н/Д"
    
    cpu_times = psutil.cpu_times_percent(interval=None)
    
    text = (
        f"🖥 <b>ДЕТАЛЬНИЙ АНАЛІЗ ПРОЦЕСОРА (CPU)</b>\n"
        f"<code>────────────────────────</code>\n"
        f"• <b>Модель:</b> {cpu_model}\n"
        f"• <b>Ядер:</b> {logical_cores} логічних ({physical_cores} фізичних)\n"
        f"• <b>Частота:</b> {freq_str}\n"
        f"• <b>Загальне завантаження:</b> {status_badge(avg_cpu)} <b>{avg_cpu:.1f}%</b>\n\n"
        f"📊 <b>Завантаження по ядрах:</b>\n"
    )
    
    for idx, core_pct in enumerate(cpu_percents):
        text += f"• Ядро #{idx}: <code>{progress_bar(core_pct, 8)}</code> {status_badge(core_pct)}\n"
        
    text += (
        f"\n📈 <b>Load Average (середнє навантаження):</b>\n"
        f"• 1 хв: <code>{load_1:.2f}</code> "
        f"({'🟡 Високе' if load_1 > (logical_cores or 1) else '🟢 Норма'})\n"
        f"• 5 хв: <code>{load_5:.2f}</code>\n"
        f"• 15 хв: <code>{load_15:.2f}</code>\n\n"
        f"⏱ <b>Розподіл часу CPU:</b>\n"
        f"• Користувач (User): <code>{getattr(cpu_times, 'user', 0):.1f}%</code>\n"
        f"• Система (System): <code>{getattr(cpu_times, 'system', 0):.1f}%</code>\n"
        f"• Очікування I/O: <code>{getattr(cpu_times, 'iowait', 0):.1f}%</code>\n"
        f"• Простій (Idle): <code>{getattr(cpu_times, 'idle', 0):.1f}%</code>\n"
        f"<code>────────────────────────</code>\n"
        f"🕒 <i>Час: {datetime.datetime.now().strftime('%H:%M:%S')}</i>"
    )
    return text

def get_ram_details() -> str:
    """Detailed RAM and Swap metrics."""
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    
    cached = getattr(mem, 'cached', 0)
    buffers = getattr(mem, 'buffers', 0)
    shared = getattr(mem, 'shared', 0)
    
    text = (
        f"🧠 <b>ДЕТАЛЬНИЙ АНАЛІЗ ПАМ'ЯТІ (RAM & SWAP)</b>\n"
        f"<code>────────────────────────</code>\n"
        f"📌 <b>Оперативна пам'ять (RAM):</b> {status_badge(mem.percent)}\n"
        f"<code>{progress_bar(mem.percent)}</code>\n"
        f"• Загальний обсяг: <b>{human_bytes(mem.total)}</b>\n"
        f"• Використано: <b>{human_bytes(mem.used)}</b> ({mem.percent}%)\n"
        f"• Доступно (Available): <b>{human_bytes(mem.available)}</b>\n"
        f"• Абсолютно вільно (Free): <b>{human_bytes(mem.free)}</b>\n"
        f"• Кеш (Cached): <b>{human_bytes(cached)}</b>\n"
        f"• Буфери (Buffers): <b>{human_bytes(buffers)}</b>\n"
        f"• Спільна (Shared): <b>{human_bytes(shared)}</b>\n\n"
        
        f"🔄 <b>Файл підкачки (SWAP):</b> {status_badge(swap.percent)}\n"
        f"<code>{progress_bar(swap.percent)}</code>\n"
        f"• Загальний обсяг: <b>{human_bytes(swap.total)}</b>\n"
        f"• Використано: <b>{human_bytes(swap.used)}</b> ({swap.percent}%)\n"
        f"• Вільно: <b>{human_bytes(swap.free)}</b>\n"
        f"• Прочитано з Swap: <b>{human_bytes(swap.sin)}</b>\n"
        f"• Записано в Swap: <b>{human_bytes(swap.sout)}</b>\n"
        f"<code>────────────────────────</code>\n"
        f"🕒 <i>Час: {datetime.datetime.now().strftime('%H:%M:%S')}</i>"
    )
    return text

def get_disk_details() -> str:
    """Detailed Disk metrics."""
    partitions = psutil.disk_partitions(all=False)
    io = psutil.disk_io_counters()
    
    text = (
        f"💾 <b>ДЕТАЛЬНИЙ АНАЛІЗ ДИСКІВ ТА ПАМ'ЯТІ</b>\n"
        f"<code>────────────────────────</code>\n"
        f"📂 <b>Монтовані файлові системи:</b>\n\n"
    )
    
    seen_mounts = set()
    for p in partitions:
        if p.mountpoint in seen_mounts:
            continue
        seen_mounts.add(p.mountpoint)
        try:
            usage = psutil.disk_usage(p.mountpoint)
            text += (
                f"🔹 <b>{p.mountpoint}</b> ({p.device}, {p.fstype}) {status_badge(usage.percent)}\n"
                f"<code>{progress_bar(usage.percent, 8)}</code>\n"
                f"  Зайнято: <b>{human_bytes(usage.used)}</b> / {human_bytes(usage.total)} "
                f"(вільно: <b>{human_bytes(usage.free)}</b>)\n\n"
            )
        except (PermissionError, FileNotFoundError):
            continue
            
    if io:
        text += (
            f"🔄 <b>Дисковий ввід/вивід (Disk I/O від старту):</b>\n"
            f"• Прочитано: <b>{human_bytes(io.read_bytes)}</b> ({io.read_count:,} операцій)\n"
            f"• Записано: <b>{human_bytes(io.write_bytes)}</b> ({io.write_count:,} операцій)\n"
        )
        
    text += (
        f"<code>────────────────────────</code>\n"
        f"🕒 <i>Час: {datetime.datetime.now().strftime('%H:%M:%S')}</i>"
    )
    return text

def get_network_details() -> str:
    """Detailed Network metrics."""
    net_io = psutil.net_io_counters()
    per_nic = psutil.net_io_counters(pernic=True)
    if_addrs = psutil.net_if_addrs()
    
    public_ip = get_public_ip()
    hostname = socket.gethostname()
    
    text = (
        f"🌐 <b>ДЕТАЛЬНИЙ АНАЛІЗ МЕРЕЖІ</b>\n"
        f"<code>────────────────────────</code>\n"
        f"• <b>Зовнішня / Основна IP:</b> <code>{public_ip}</code>\n"
        f"• <b>Ім'я сервера:</b> <code>{hostname}</code>\n\n"
        
        f"📊 <b>Загальний трафік (з моменту завантаження):</b>\n"
        f"• ⬇️ Вхідний (Rx): <b>{human_bytes(net_io.bytes_recv)}</b> ({net_io.packets_recv:,} пак.)\n"
        f"• ⬆️ Вихідний (Tx): <b>{human_bytes(net_io.bytes_sent)}</b> ({net_io.packets_sent:,} пак.)\n"
        f"• ⚠️ Помилок входу/виходу: <code>{net_io.errin} / {net_io.errout}</code>\n"
        f"• 🚫 Скинутих пакетів: <code>{net_io.dropin} / {net_io.dropout}</code>\n\n"
        f"🔌 <b>Мережеві інтерфейси:</b>\n"
    )
    
    for if_name, addrs in if_addrs.items():
        ip_list = [addr.address for addr in addrs if addr.family == socket.AF_INET]
        if not ip_list:
            continue
        nic_stat = per_nic.get(if_name)
        nic_info = f"<code>{', '.join(ip_list)}</code>"
        traffic_info = ""
        if nic_stat:
            traffic_info = f" (⬇️ {human_bytes(nic_stat.bytes_recv)} | ⬆️ {human_bytes(nic_stat.bytes_sent)})"
        text += f"• <b>{if_name}:</b> {nic_info}{traffic_info}\n"
        
    text += (
        f"<code>────────────────────────</code>\n"
        f"🕒 <i>Час: {datetime.datetime.now().strftime('%H:%M:%S')}</i>"
    )
    return text

def get_processes_text(sort_by: str = "cpu", limit: int = 10) -> str:
    """Return top processes sorted by CPU or RAM."""
    import subprocess
    
    # Count totals via psutil
    total_running = 0
    total_sleeping = 0
    total_zombie = 0
    total_count = 0
    
    for p in psutil.process_iter(['status']):
        try:
            total_count += 1
            st = p.status()
            if st == psutil.STATUS_RUNNING:
                total_running += 1
            elif st == psutil.STATUS_SLEEPING:
                total_sleeping += 1
            elif st == psutil.STATUS_ZOMBIE:
                total_zombie += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    title = "ЗА НАВАНТАЖЕННЯМ CPU" if sort_by == 'cpu' else "ЗА ВИКОРИСТАННЯМ RAM"
    sort_flag = "--sort=-pcpu" if sort_by == 'cpu' else "--sort=-pmem"
    
    lines = [
        f"⚡ <b>ТОП ПРОЦЕСІВ ({title})</b>",
        f"<code>────────────────────────</code>",
        f"⚙️ Всього процесів: <b>{total_count}</b> "
        f"(🏃 {total_running} running, 💤 {total_sleeping} sleeping, 🧟 {total_zombie} zombie)\n",
        f"<code>PID     %CPU  %MEM  USER         COMM</code>",
        f"<code>─────────────────────────────────────</code>"
    ]
    
    try:
        res = subprocess.run(
            ["ps", "-eo", "pid:7,pcpu:6,pmem:6,user:12,comm:15", sort_flag],
            capture_output=True,
            text=True,
            timeout=2.0
        )
        if res.returncode == 0:
            out_lines = [l for l in res.stdout.strip().split('\n')[1:] if l.strip()]
            # filter out the ps command itself
            filtered = [l for l in out_lines if not l.endswith(' ps')][:limit]
            for row in filtered:
                lines.append(f"<code>{row}</code>")
    except Exception:
        lines.append("<code>Не вдалося отримати список процесів</code>")
        
    lines.append(f"<code>─────────────────────────────────────</code>")
    lines.append(f"🕒 <i>Час: {datetime.datetime.now().strftime('%H:%M:%S')}</i>")
    return "\n".join(lines)

def get_system_info() -> str:
    """Full system and OS specifications."""
    uname = platform.uname()
    boot_time = psutil.boot_time()
    uptime_sec = time.time() - boot_time
    boot_dt = datetime.datetime.fromtimestamp(boot_time).strftime('%d.%m.%Y %H:%M:%S')
    server_time = datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')
    
    # OS Pretty name
    os_name = "Linux"
    if os.path.exists('/etc/os-release'):
        try:
            with open('/etc/os-release') as f:
                for line in f:
                    if line.startswith('PRETTY_NAME='):
                        os_name = line.split('=', 1)[1].strip().strip('"')
                        break
        except Exception:
            pass
            
    users = psutil.users()
    users_lines = []
    for u in users:
        started = datetime.datetime.fromtimestamp(u.started).strftime('%H:%M')
        host_str = f" з {u.host}" if u.host else ""
        users_lines.append(f"• 👤 <b>{u.name}</b> (термінал <code>{u.terminal}</code>{host_str}, вхід о {started})")
        
    users_text = "\n".join(users_lines) if users_lines else "• Немає активних сесій"
    
    text = (
        f"ℹ️ <b>ІНФОРМАЦІЯ ПРО СИСТЕМУ ТА СЕРВЕР</b>\n"
        f"<code>────────────────────────</code>\n"
        f"• <b>Операційна система:</b> {os_name}\n"
        f"• <b>Ядро (Kernel):</b> <code>{uname.release}</code>\n"
        f"• <b>Архітектура:</b> <code>{uname.machine}</code>\n"
        f"• <b>Ім'я вузла (Hostname):</b> <code>{uname.node}</code>\n"
        f"• <b>IP сервера:</b> <code>{get_public_ip()}</code>\n"
        f"• <b>Запуск системи:</b> {boot_dt}\n"
        f"• <b>Час роботи (Uptime):</b> <b>{format_timedelta(uptime_sec)}</b>\n"
        f"• <b>Поточний час сервера:</b> {server_time}\n\n"
        f"👥 <b>Активні користувачі (SSH/Login):</b>\n"
        f"{users_text}\n"
        f"<code>────────────────────────</code>"
    )
    return text

def check_alerts(settings: Dict[str, Any]) -> List[str]:
    """Check if any metric exceeds alert thresholds."""
    if not settings.get("alerts_enabled", True):
        return []
        
    alerts = []
    
    # CPU Check
    cpu_pct = psutil.cpu_percent(interval=None)
    cpu_thresh = settings.get("alert_cpu_threshold", 85.0)
    if cpu_pct >= cpu_thresh:
        alerts.append(f"⚠️ <b>Критичне навантаження CPU!</b>\nПоточне використання: <b>{cpu_pct:.1f}%</b> (ліміт: {cpu_thresh}%)")
        
    # RAM Check
    mem = psutil.virtual_memory()
    ram_thresh = settings.get("alert_ram_threshold", 90.0)
    if mem.percent >= ram_thresh:
        alerts.append(f"⚠️ <b>Критично мало оперативної пам'яті (RAM)!</b>\nВикористано: <b>{mem.percent:.1f}%</b> ({human_bytes(mem.used)} / {human_bytes(mem.total)})")
        
    # Disk Check
    disk_thresh = settings.get("alert_disk_threshold", 90.0)
    try:
        root_disk = psutil.disk_usage('/')
        if root_disk.percent >= disk_thresh:
            alerts.append(f"⚠️ <b>Критично мало місця на диску (/)!</b>\nЗайнято: <b>{root_disk.percent:.1f}%</b> ({human_bytes(root_disk.used)} / {human_bytes(root_disk.total)})")
    except Exception:
        pass
        
    return alerts
