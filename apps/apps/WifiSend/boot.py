import network
import uos
import usocket as socket
import ure as re
import time
import gc
from machine import Pin
from button_n import Button

# 绝对路径
HTML_TEMPLATE_PATH = '/sd/apps/WifiSend/www/index.html'
MANAGER_TEMPLATE_PATH = '/sd/apps/WifiSend/www/manager.html'
SETTINGS_TEMPLATE_PATH = '/sd/apps/WifiSend/www/settings.html'

print("WWW路径:", '/sd/apps/WifiSend/www')

# 导入显示相关库（参照boot.py）
import vga2_8x16 as font
import vga2_16x32 as font_16x32
import tft_config
import st7789

# 初始化屏幕
tft = tft_config.config(0)
tft.init()

# 立即显示背景图，避免开机黑屏
print("加载背景图...")
try:
    tft.jpg('/sd/apps/WifiSend/main.jpg', 0, 0, st7789.SLOW)
except Exception as e:
    print(f"加载背景图失败: {e}")
    tft.fill(st7789.BLACK)

# 初始化按键
buttons = Button()
exit_program = False

def draw_wifi_info():
    """在背景图上显示WiFi热点信息"""
    # 先显示背景图
    tft.jpg('/sd/apps/WifiSend/main.jpg', 0, 0, st7789.SLOW)


def cleanup_resources():
    """释放资源"""
    global ap
    # 关闭WiFi
    if ap:
        ap.active(False)
        print("WiFi closed")
    
    # 清屏
    tft.fill(st7789.BLACK)
    
    # 释放按键
    buttons.deinit()
    
    # 垃圾回收
    gc.collect()
    print("Resources cleaned up")

def center_button_long_press_callback():
    """长按中间键退出程序"""
    global exit_program
    exit_program = True
    print("Exit signal received")

def url_decode(s):
    result = bytearray()
    i = 0
    while i < len(s):
        if s[i] == '%' and i + 2 < len(s):
            try:
                hex_val = int(s[i+1:i+3], 16)
                result.append(hex_val)
                i += 3
            except:
                result.append(ord(s[i]))
                i += 1
        elif s[i] == '+':
            result.append(ord(' '))
            i += 1
        else:
            result.append(ord(s[i]))
            i += 1
    try:
        return bytes(result).decode('utf-8')
    except:
        return s

def init_wifi():
    ap = network.WLAN(network.AP_IF)
    ap.active(False)
    time.sleep(0.5)
    
    ap.config(
        essid='OpenStickT1',
        password='12345678',
        max_clients=4,
        authmode=4
    )
    
    ap.ifconfig(('192.168.4.1', '255.255.255.0', '192.168.4.1', '192.168.4.1'))
    
    ap.active(True)
    start_time = time.ticks_ms()
    timeout = 10000
    
    while not ap.active():
        if time.ticks_ms() - start_time > timeout:
            print("WiFi启动超时，重试...")
            ap.active(False)
            time.sleep(0.5)
            ap.active(True)
            start_time = time.ticks_ms()
        time.sleep(0.1)
    
    print("热点已启动，IP:", ap.ifconfig()[0])
    print("Captive Portal 已启用，连接后会自动弹出网页")
    return ap

ap = init_wifi()

HOST = '0.0.0.0'
PORT = 80
MAX_CONNECTIONS = 5
connection_count = 0

SD_ROOT = '/sd/image'
CONFIG_PATH = '/sd/apps/config.json'

HTML_TEMPLATE = None
MANAGER_TEMPLATE = None
SETTINGS_TEMPLATE = None

def load_html_template():
    global HTML_TEMPLATE, MANAGER_TEMPLATE, SETTINGS_TEMPLATE
    try:
        with open(HTML_TEMPLATE_PATH, 'r') as f:
            HTML_TEMPLATE = f.read()
        print("主页模板加载成功")
    except Exception as e:
        print(f"加载主页模板失败: {e}")
        HTML_TEMPLATE = None
    
    try:
        with open(MANAGER_TEMPLATE_PATH, 'r') as f:
            MANAGER_TEMPLATE = f.read()
        print("管理页面模板加载成功")
    except Exception as e:
        print(f"加载管理页面模板失败: {e}")
        MANAGER_TEMPLATE = None
    
    try:
        with open(SETTINGS_TEMPLATE_PATH, 'r') as f:
            SETTINGS_TEMPLATE = f.read()
        print("设置页面模板加载成功")
    except Exception as e:
        print(f"加载设置页面模板失败: {e}")
        SETTINGS_TEMPLATE = None

def list_files(path=SD_ROOT):
    try:
        files = uos.listdir(path)
    except OSError:
        files = []
    
    file_list = ''
    for f in files:
        full_path = path + '/' + f
        try:
            is_dir = uos.stat(full_path)[0] & 0x4000
            safe_id = ''
            for c in f:
                if ('a' <= c <= 'z') or ('A' <= c <= 'Z') or ('0' <= c <= '9'):
                    safe_id += c
                else:
                    safe_id += '-'
            if is_dir:
                file_list += '<li class="file-item dir-item" data-path="%s"><label class="checkbox-wrap"><input type="checkbox" class="delete-checkbox" value="%s" data-type="dir"></label><a href="/browse?dir=%s" class="dir-link"><div class="file-icon">📁</div><div class="file-info"><div class="file-name">%s</div></div></a></li>' % (full_path, full_path, full_path, f)
            else:
                ext = f.lower().split('.')[-1] if '.' in f else ''
                is_image = ext in ['bmp', 'jpg', 'jpeg']
                if is_image:
                    icon_html = '<img src="/download?file=%s" class="file-preview-img" alt="%s">' % (full_path.replace(' ', '%20'), f)
                else:
                    icon_html = '<div class="file-icon">📄</div>'
                file_list += '<li class="file-item %s" data-path="%s"><label class="checkbox-wrap"><input type="checkbox" class="delete-checkbox" value="%s" data-type="file"></label>%s<div class="file-info"><div class="file-name">%s</div></div></li>' % ('image-item' if is_image else '', full_path, full_path, icon_html, f)
        except OSError:
            continue
    
    return file_list

def html_page(file_list, current_path=SD_ROOT, is_manager=False):
    global HTML_TEMPLATE, MANAGER_TEMPLATE
    if HTML_TEMPLATE is None or MANAGER_TEMPLATE is None:
        load_html_template()
    
    template = MANAGER_TEMPLATE if is_manager else HTML_TEMPLATE
    
    if template is None:
        return '<html><body><h1>错误：无法加载HTML模板</h1><p>请确保 /sd/www/index.html 文件存在</p></body></html>'
    
    path_display = current_path
    
    back_button = '<a href="/browse?dir=%s" class="btn btn-back">⬅️ 返回上一级</a>' % ('/'.join(current_path.split('/')[:-1]) if current_path.count('/') > 1 else SD_ROOT) if current_path != SD_ROOT else ''
    
    html = template.replace('{{PATH_DISPLAY}}', path_display)
    html = html.replace('{{BACK_BUTTON}}', back_button)
    html = html.replace('{{FILE_LIST}}', file_list)
    html = html.replace('{{CURRENT_PATH}}', current_path.replace(' ', '%20'))
    
    return html

load_html_template()

# 显示WiFi热点信息
draw_wifi_info()

# 注册按键回调
buttons.register_callback('center', 'long', center_button_long_press_callback)

def check_wifi():
    global ap
    if not ap.active():
        print("WiFi连接断开，尝试重新连接...")
        ap = init_wifi()
    return ap.active()

def serve():
    global connection_count, exit_program
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(MAX_CONNECTIONS)
    s.settimeout(0.1)  # 缩短超时，便于检测按键
    print("HTTP 服务器启动，端口", PORT)

    try:
        while not exit_program:
            try:
                if not check_wifi():
                    time.sleep(0.1)
                    continue
                    
                conn, addr = s.accept()
                conn.settimeout(60)
                
                if connection_count >= MAX_CONNECTIONS:
                    conn.send('HTTP/1.0 503 Service Unavailable\r\nContent-Type: text/plain\r\n\r\n服务器繁忙，请稍后重试')
                    conn.close()
                    continue
                
                connection_count += 1
                print("连接来自", addr, "当前连接数:", connection_count)
                
                try:
                    request = conn.recv(4096)
                    if not request:
                        conn.close()
                        connection_count -= 1
                        continue
                    
                    request_str = str(request)
                    print("请求:", request_str[:100])

                    captive_domains = [
                        'captive.apple.com',
                        'apple.com',
                        'connectivitycheck.gstatic.com',
                        'www.gstatic.com',
                        'google.com',
                        'www.google.com',
                        'msftconnecttest.com',
                        'www.msftconnecttest.com',
                        'microsoft.com',
                        'www.microsoft.com',
                        'nmcheck.gnome.org',
                        'canonical.com',
                        'detectportal.firefox.com'
                    ]
                    
                    has_captive_domain = False
                    for domain in captive_domains:
                        if domain in request_str.lower():
                            has_captive_domain = True
                            break
                    
                    if has_captive_domain or b'/generate_204' in request or b'/ncsi.txt' in request or b'/connecttest.txt' in request:
                        conn.send('HTTP/1.0 302 Found\r\n')
                        conn.send('Location: http://192.168.4.1/\r\n')
                        conn.send('Cache-Control: no-cache, no-store, must-revalidate\r\n')
                        conn.send('Pragma: no-cache\r\n')
                        conn.send('Expires: 0\r\n')
                        conn.send('\r\n')
                        conn.close()
                        connection_count -= 1
                        print("Captive Portal: 重定向到主页")
                        continue

                    if b'POST /upload' in request:
                        try:
                            conn.settimeout(300)
                            upload_path = SD_ROOT
                            request_line_end = request.find(b'\r\n')
                            if request_line_end != -1:
                                request_line = request[:request_line_end].decode()
                                print(f"请求行: {request_line}")
                                path_start = request_line.find('?path=')
                                if path_start != -1:
                                    path_end = request_line.find(' ', path_start)
                                    if path_end != -1:
                                        path_param = request_line[path_start+6:path_end]
                                        upload_path = url_decode(path_param)
                                        print(f"从URL获取到上传路径: '{upload_path}'")
                            
                            content_length = 0
                            if b'Content-Length:' in request:
                                cl_start = request.find(b'Content-Length:') + 15
                                cl_end = request.find(b'\r\n', cl_start)
                                if cl_end != -1:
                                    try:
                                        content_length = int(request[cl_start:cl_end])
                                        print(f"需要接收: {content_length} 字节")
                                    except ValueError:
                                        pass
                            
                            idx = request.find(b'boundary=')
                            if idx == -1:
                                print("找不到boundary")
                                conn.send('HTTP/1.0 400 Bad Request\r\n\r\n')
                                conn.close()
                                connection_count -= 1
                                continue
                            
                            idx += 9
                            if request[idx:idx+2] == b'--':
                                idx += 2
                            end = request.find(b'\r\n', idx)
                            boundary = request[idx:end].decode()
                            boundary_bytes = b'--' + boundary.encode()
                            final_boundary = boundary_bytes + b'--'
                            print(f"boundary: {boundary}")
                            
                            while True:
                                header_end = request.find(b'\r\n\r\n')
                                if header_end != -1:
                                    break
                                chunk = conn.recv(2048)
                                if not chunk:
                                    break
                                request += chunk
                            
                            body_start = header_end + 4
                            buffer = request[body_start:]
                            current_file = None
                            current_f = None
                            file_count = 0
                            header_size = body_start
                            total_received = len(request)
                            
                            while True:
                                bound_idx = buffer.find(boundary_bytes)
                                
                                if bound_idx != -1:
                                    if current_f and bound_idx > 0:
                                        to_write = buffer[:bound_idx]
                                        if to_write.endswith(b'\r\n'):
                                            to_write = to_write[:-2]
                                        if to_write:
                                            current_f.write(to_write)
                                    
                                    if current_f:
                                        current_f.close()
                                        print(f"文件保存完成: {current_file}")
                                    
                                    header_part = buffer[bound_idx + len(boundary_bytes):]
                                    
                                    if header_part.startswith(b'--'):
                                        break
                                    
                                    fname_idx = header_part.find(b'filename="')
                                    if fname_idx != -1:
                                        fname_start = fname_idx + 10
                                        fname_end = header_part.find(b'"', fname_start)
                                        if fname_end != -1:
                                            filename = header_part[fname_start:fname_end].decode()
                                            if filename:
                                                content_idx = header_part.find(b'\r\n\r\n', fname_end)
                                                if content_idx != -1:
                                                    try:
                                                        filename_decoded = filename.decode('utf-8') if isinstance(filename, bytes) else filename
                                                        safe_filename = ''
                                                        for c in filename_decoded:
                                                            if c.isalnum() or c in '._-':
                                                                safe_filename += c
                                                            else:
                                                                safe_filename += '_'
                                                        current_file = upload_path + '/' + safe_filename
                                                    except:
                                                        safe_filename = filename if isinstance(filename, str) else filename.decode('utf-8', errors='ignore')
                                                        current_file = upload_path + '/' + safe_filename
                                                    ext = safe_filename.lower().split('.')[-1] if '.' in safe_filename else ''
                                                    if ext not in ['bmp', 'jpg', 'jpeg']:
                                                        print(f"文件类型不允许: {safe_filename}")
                                                        buffer = header_part[content_idx + 4:]
                                                        continue
                                                    try:
                                                        current_f = open(current_file, 'wb')
                                                        file_count += 1
                                                        print(f"开始保存: {current_file}")
                                                        buffer = header_part[content_idx + 4:]
                                                        continue
                                                    except Exception as e:
                                                        print(f"打开文件错误: {e}")
                                                        current_f = None
                                    
                                    buffer = b''
                                else:
                                    if current_f and len(buffer) > 0:
                                        keep_len = min(len(buffer), len(boundary_bytes) + 4)
                                        to_write = buffer[:-keep_len] if len(buffer) > keep_len else buffer
                                        if to_write:
                                            try:
                                                current_f.write(to_write)
                                            except Exception as e:
                                                print(f"写入文件错误: {e}")
                                                current_f.close()
                                                current_f = None
                                                continue
                                        buffer = buffer[-keep_len:] if len(buffer) > keep_len else buffer
                                
                                try:
                                    chunk = conn.recv(4096)
                                    if not chunk:
                                        break
                                    buffer += chunk
                                    total_received += len(chunk)
                                    
                                    if total_received % 40960 == 0:
                                        print(f"已接收: {total_received}/{header_size + content_length} 字节")
                                except Exception as e:
                                    break
                            
                            if current_f:
                                try:
                                    current_f.close()
                                    if len(buffer) > 0 and current_file:
                                        try:
                                            with open(current_file, 'ab') as f:
                                                to_write = buffer
                                                if to_write.endswith(b'\r\n'):
                                                    to_write = to_write[:-2]
                                                f.write(to_write)
                                        except Exception as e:
                                            print(f"写入剩余数据错误: {e}")
                                    print(f"文件保存完成: {current_file}")
                                except Exception as e:
                                    print(f"关闭文件错误: {e}")
                            
                            print(f"共保存 {file_count} 个文件")
                            
                            conn.send('HTTP/1.0 200 OK\r\nContent-type: text/plain\r\n\r\n')
                            conn.send('OK')
                            conn.close()
                            connection_count -= 1
                            continue
                        
                        except Exception as e:
                            print(f"上传错误: {e}")
                            import sys
                            sys.print_exception(e)
                            conn.send('HTTP/1.0 500 Internal Server Error\r\n\r\n')
                            conn.close()
                            connection_count -= 1
                            continue

                    m = re.search(r'/download\?file=([^\s]+)', request_str)
                    if m:
                        file_path = url_decode(m.group(1))
                        try:
                            conn.settimeout(300)
                            file_stat = uos.stat(file_path)
                            file_size = file_stat[6]
                            filename = file_path.split('/')[-1]
                            
                            conn.send('HTTP/1.1 200 OK\r\n')
                            conn.send('Content-Type: application/octet-stream\r\n')
                            conn.send('Content-Disposition: attachment; filename="download"\r\n')
                            conn.send('Accept-Ranges: bytes\r\n')
                            conn.send('Content-Length: %d\r\n\r\n' % file_size)
                            chunk_size = 2048
                            sent = 0
                            with open(file_path, 'rb') as f:
                                while True:
                                    chunk = f.read(chunk_size)
                                    if not chunk:
                                        break
                                    conn.send(chunk)
                                    sent += len(chunk)
                            conn.close()
                            connection_count -= 1
                            continue
                        except OSError:
                            conn.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
                            conn.send('<!DOCTYPE html><html><head><meta charset="utf-8"><style>body{font-family:Arial,sans-serif;max-width:600px;margin:50px auto;text-align:center;background:#f5f5f5}.container{background:white;padding:40px;border-radius:8px;box-shadow:0 2px 4px rgba(0,0,0,0.1)}.error{color:#f44336;font-size:28px;margin-bottom:20px}.btn{display:inline-block;background:#0066cc;color:white;padding:12px 30px;text-decoration:none;border-radius:4px;margin-top:20px}.btn:hover{background:#0052a3}</style></head><body><div class="container"><div class="error">✗ 下载失败！</div><p>文件不存在或无法访问</p><a href="/" class="btn">返回首页</a></div></body></html>')
                            conn.close()
                            connection_count -= 1
                            continue
                    
                    m = re.search(r'/delete\?file=([^\s]+)', request_str)
                    if m:
                        file_path = url_decode(m.group(1))
                        try:
                            uos.remove(file_path)
                            print(f"删除文件: {file_path}")
                        except OSError as e:
                            print(f"删除失败: {e}")
                        
                        if '/' in file_path:
                            dir_path = '/'.join(file_path.split('/')[:-1])
                            redirect_url = '/browse?dir=' + dir_path
                        else:
                            redirect_url = '/'
                        
                        conn.send('HTTP/1.0 302 Found\r\n')
                        conn.send('Location: ' + redirect_url + '\r\n')
                        conn.send('Cache-Control: no-cache, no-store, must-revalidate\r\n')
                        conn.send('Pragma: no-cache\r\n')
                        conn.send('Expires: 0\r\n')
                        conn.send('\r\n')
                        conn.close()
                        connection_count -= 1
                        continue

                    if b'GET /api/health' in request or b'GET /health' in request:
                        conn.send('HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n')
                        conn.send('{"status": "ok"}')
                        conn.close()
                        connection_count -= 1
                        continue

                    if b'POST /api/delete' in request:
                        try:
                            header_end = request.find(b'\r\n\r\n')
                            if header_end == -1:
                                body_start = len(request)
                            else:
                                body_start = header_end + 4
                            
                            content_length = 0
                            if b'Content-Length:' in request:
                                cl_start = request.find(b'Content-Length:') + 15
                                cl_end = request.find(b'\r\n', cl_start)
                                if cl_end != -1:
                                    content_length = int(request[cl_start:cl_end])
                            
                            total_needed = body_start + content_length
                            while len(request) < total_needed:
                                try:
                                    chunk = conn.recv(4096)
                                    if not chunk:
                                        break
                                    request += chunk
                                except:
                                    break
                            
                            body = request[body_start:body_start + content_length]
                            
                            import ujson
                            try:
                                data = ujson.loads(body)
                                files = data.get('files', [])
                                
                                deleted_count = 0
                                errors = []
                                for file_info in files:
                                    file_path = file_info.get('path', '')
                                    if file_path:
                                        try:
                                            uos.remove(file_path)
                                            deleted_count += 1
                                            print(f"删除: {file_path}")
                                        except OSError as e:
                                            errors.append({'path': file_path, 'error': str(e)})
                                            print(f"删除失败 {file_path}: {e}")
                                
                                response = {'success': True, 'deleted': deleted_count, 'errors': errors}
                                conn.send('HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n')
                                conn.send(ujson.dumps(response))
                            except Exception as e:
                                print(f"批量删除解析错误: {e}")
                                conn.send('HTTP/1.0 400 Bad Request\r\nContent-Type: application/json\r\n\r\n')
                                conn.send('{"error": "Invalid request"}')
                        except Exception as e:
                            print(f"批量删除错误: {e}")
                            conn.send('HTTP/1.0 500 Internal Server Error\r\nContent-Type: application/json\r\n\r\n')
                            conn.send('{"error": str(e)}')
                        conn.close()
                        connection_count -= 1
                        continue

                    m = re.search(r'/browse\?dir=([^\s]+)', request_str)
                    if m:
                        dir_path = url_decode(m.group(1))
                        files_html = list_files(dir_path)
                        conn.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
                        conn.send(html_page(files_html, dir_path))
                        conn.close()
                        connection_count -= 1
                        continue

                    m = re.search(r'/api/list', request_str)
                    if m:
                        import ujson
                        try:
                            dir_param = request_str.split('?dir=')[1].split(' ')[0] if '?dir=' in request_str else SD_ROOT
                            dir_path = url_decode(dir_param)
                        except:
                            dir_path = SD_ROOT
                        try:
                            files = uos.listdir(dir_path)
                            file_list_json = []
                            for f in files:
                                full_path = dir_path + '/' + f
                                try:
                                    is_dir = uos.stat(full_path)[0] & 0x4000
                                    safe_id = ''
                                    for c in f:
                                        if ('a' <= c <= 'z') or ('A' <= c <= 'Z') or ('0' <= c <= '9'):
                                            safe_id += c
                                        else:
                                            safe_id += '-'
                                    file_list_json.append({
                                        'name': f,
                                        'path': full_path,
                                        'type': 'dir' if is_dir else 'file',
                                        'safeId': safe_id
                                    })
                                except:
                                    continue
                            import ujson
                            response_data = ujson.dumps({'files': file_list_json, 'path': dir_path})
                            conn.send('HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n')
                            conn.send(response_data)
                        except Exception as e:
                            print(f"获取文件列表错误: {e}")
                            conn.send('HTTP/1.0 500 OK\r\nContent-Type: application/json\r\n\r\n')
                            conn.send('{"error": "Failed to list files"}')
                        conn.close()
                        connection_count -= 1
                        continue

                    if b'GET /manager' in request:
                        files_html = list_files(SD_ROOT)
                        conn.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
                        conn.send(html_page(files_html, SD_ROOT, is_manager=True))
                        conn.close()
                        connection_count -= 1
                        continue

                    if b'GET /settings' in request:
                        if SETTINGS_TEMPLATE is None:
                            load_html_template()
                        if SETTINGS_TEMPLATE:
                            conn.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
                            conn.send(SETTINGS_TEMPLATE)
                        else:
                            conn.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
                            conn.send('<html><body><h1>设置页面加载失败</h1><a href="/">返回首页</a></body></html>')
                        conn.close()
                        connection_count -= 1
                        continue

                    if b'GET /config.json' in request:
                        try:
                            with open(CONFIG_PATH, 'r') as f:
                                config_content = f.read()
                            conn.send('HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n')
                            conn.send(config_content)
                        except Exception as e:
                            print(f"读取配置文件错误: {e}")
                            conn.send('HTTP/1.0 500 Internal Server Error\r\nContent-Type: application/json\r\n\r\n')
                            conn.send('{"error": "Failed to read config"}')
                        conn.close()
                        connection_count -= 1
                        continue

                    if b'POST /save_config' in request:
                        try:
                            header_end = request.find(b'\r\n\r\n')
                            if header_end == -1:
                                body_start = len(request)
                            else:
                                body_start = header_end + 4
                            
                            content_length = 0
                            if b'Content-Length:' in request:
                                cl_start = request.find(b'Content-Length:') + 15
                                cl_end = request.find(b'\r\n', cl_start)
                                if cl_end != -1:
                                    content_length = int(request[cl_start:cl_end])
                            
                            total_needed = body_start + content_length
                            while len(request) < total_needed:
                                try:
                                    chunk = conn.recv(4096)
                                    if not chunk:
                                        break
                                    request += chunk
                                except:
                                    break
                            
                            body = request[body_start:body_start + content_length]
                            
                            import ujson
                            try:
                                data = ujson.loads(body)
                                new_length = data.get('light_stick_length', 3)
                                auto_shutdown = data.get('auto_shutdown', True)
                                auto_shutdown_seconds = data.get('auto_shutdown_seconds', 300)
                                red_green_swap = data.get('red_green_swap', False)

                                with open(CONFIG_PATH, 'r') as f:
                                    config = ujson.loads(f.read())

                                config['light_stick_length'] = new_length
                                config['auto_shutdown'] = auto_shutdown
                                config['auto_shutdown_seconds'] = auto_shutdown_seconds
                                config['red_green_swap'] = red_green_swap

                                with open(CONFIG_PATH, 'w') as f:
                                    f.write(ujson.dumps(config))

                                print(f"配置已更新: light_stick_length={new_length}, auto_shutdown={auto_shutdown}, auto_shutdown_seconds={auto_shutdown_seconds}, red_green_swap={red_green_swap}")
                                conn.send('HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n')
                                conn.send('{"success": true}')
                            except Exception as e:
                                print(f"保存配置解析错误: {e}")
                                conn.send('HTTP/1.0 400 Bad Request\r\nContent-Type: application/json\r\n\r\n')
                                conn.send('{"error": "Invalid request"}')
                        except Exception as e:
                            print(f"保存配置错误: {e}")
                            conn.send('HTTP/1.0 500 Internal Server Error\r\nContent-Type: application/json\r\n\r\n')
                            conn.send('{"error": "Failed to save config"}')
                        conn.close()
                        connection_count -= 1
                        continue

                    conn.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
                    if HTML_TEMPLATE:
                        conn.send(HTML_TEMPLATE)
                    else:
                        conn.send('<html><body><h1>错误：无法加载主页</h1></body></html>')
                    conn.close()
                    connection_count -= 1

                except Exception as e:
                    print("请求处理错误:", e)
                    try:
                        conn.close()
                    except:
                        pass
                    connection_count -= 1

            except OSError as e:
                if e.args and (e.args[0] == 110 or e.args[0] == 116):
                    continue
                else:
                    print("Socket错误:", e)
                    time.sleep(0.1)
            except Exception as e:
                print("服务器错误:", e)
                try:
                    conn.close()
                except:
                    pass
                time.sleep(0.1)
    finally:
        # 清理资源
        cleanup_resources()
        print("程序退出")

serve()
