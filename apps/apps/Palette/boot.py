from button import Button
from machine import Pin
import neopixel
import time
import gc

import tft_config
import st7789
tft = tft_config.config(0)
tft.init()
 
tft.jpg('/sd/apps/Palette/main.jpg', 0, 0, st7789.SLOW)

# 定义按钮对象
buttons = Button()

# 电源使能引脚
enable_pin = Pin(43, Pin.OPEN_DRAIN) # 电源使能引脚，根据实际情况选择正确的引脚
enable_pin.value(1)# 设置高阻态，关断电源输出

import pm
pm.init()
pm.set_power_state(pm.VCC_OUTPUT)

# 定义最大分辨率
MAX_RESOLUTION = 144
try:
    import ujson
    with open('/sd/apps/config.json', 'r') as f:
        config = ujson.loads(f.read())
        light_stick_length = config.get('light_stick_length', 3)
        MAX_RESOLUTION = light_stick_length * 48
        print(f"Loaded light_stick_length: {light_stick_length}, MAX_RESOLUTION: {MAX_RESOLUTION}")
except Exception as e:
    print(f"Failed to load config, using default MAX_RESOLUTION=144: {e}")

np = neopixel.NeoPixel(Pin(13), MAX_RESOLUTION)

interval_mode = False  # 默认开启间隔亮模式


brightness = 1  # 初始化亮度为2
color = 0
led_state = False  # 初始化LED状态为开
exit_program = False  # 退出标志位

# 定义最小亮度因子，避免颜色完全变暗
MIN_BRIGHTNESS_FACTOR = 0.1

# 计算亮度因子
brightness_factor = max(brightness / 4, MIN_BRIGHTNESS_FACTOR)

# 定义颜色列表
colors = [
    0xF800,  # 红色
    0xFC00,  # 橙色
    0xFFE0,  # 黄色
    0x87E0,  # 浅绿
    0x07E0,  # 绿色
    0x07FF,  # 青色
    0x03FF,  # 天蓝
    0x001F,  # 蓝色
    0x780F,  # 紫色
    0xF81F,  # 粉色
    0x8410,  # 灰色
    0xFFFF,  # 白色
    0x8506,  # 彩色
    0x8523   # 彩色2
]

def apply_brightness(color, brightness):
    # 颜色分量
    r = (color >> 11) & 0x1F
    g = (color >> 5) & 0x3F
    b = color & 0x1F
    
    # 亮度因子
    factor = max(brightness / 4.0, 0.1)  # 确保最低亮度不为0
    
    if color == 0xFFFF:  # 如果颜色是白色
        # 计算原始RGB值
        r = int(31 * factor)  # 31是白色的最大红色值
        g = int(63 * factor)  # 63是白色的最大绿色值
        b = int(31 * factor)  # 31是白色的最大蓝色值
    else:
        r = int((r / 31.0) * factor * 31)
        g = int((g / 63.0) * factor * 63)
        b = int((b / 31.0) * factor * 31)
    
    # 确保颜色在有效范围内
    r = min(max(r, 0), 31)
    g = min(max(g, 0), 63)
    b = min(max(b, 0), 31)
    
    return (r << 11) | (g << 5) | b



def wheel(pos):
    """Generate rainbow colors across 0-255 positions."""
    if pos < 85:
        return (pos * 3, 255 - pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return (255 - pos * 3, 0, pos * 3)
    else:
        pos -= 170
        return (0, pos * 3, 255 - pos * 3)

# 按钮回调函数
def left_button_short_press_callback():
    global brightness
    if brightness > 0:  
        brightness -= 1
        tft.fill_circle(41+(13*(brightness+1)), 25, 4, st7789.BLACK)
        tft.fill_circle(41+(13*brightness), 25, 4, st7789.WHITE)
 

def right_button_short_press_callback():
    global brightness
    if brightness < 4:  
        brightness += 1
        tft.fill_circle(41+(13*(brightness-1)), 25, 4, st7789.BLACK)
        tft.fill_circle(41+(13*brightness), 25, 4, st7789.WHITE)
    

def up_button_short_press_callback():
    global color
    clear_color_circle(color)
    
    color -= 1
    if color < 0:
        color = 13
    
    show_color_circle(color)
    update_center_circle(color)

def down_button_short_press_callback():
    global color
    clear_color_circle(color)
    
    color += 1
    if color > 13:
        color = 0
    
    show_color_circle(color)
    update_center_circle(color)
    
def up_button_long_press_callback():
    global interval_mode
    interval_mode = not interval_mode  # 切换间隔亮与否
    if interval_mode:
        print("间隔亮模式已开启")
    else:
        print("不间隔亮模式已开启")


def update_center_circle(color):
    center_x = tft.width() // 2
    center_y = (tft.height() // 2) - 30
    radius = 25

    if color == 12:  # 彩色
        rainbow_colors = [0xF800, 0xFC00, 0xFFE0, 0x87E0, 0x07E0, 0x07FF, 0x03FF, 0x001F]
        for i in range(len(rainbow_colors)):
            tft.fill_circle(center_x, center_y, int(radius * (0.8 ** i)), rainbow_colors[i])
    elif color == 13:  # 彩色2
        rainbow_colors = [0x001F, 0x03FF, 0x07FF, 0x07E0, 0x87E0, 0xFFE0, 0xFC00, 0xF800]
        for i in range(len(rainbow_colors)):
            tft.fill_circle(center_x, center_y, int(radius * (0.8 ** i)), rainbow_colors[i])
    else:
        tft.fill_circle(center_x, center_y, radius, colors[color])

def show_color_circle(color):
    if color <= 6:
        tft.fill_circle(25, 49 + (13 * color), 4, st7789.WHITE)
    else:
        tft.fill_circle(109, 49 + (13 * (color - 7)), 4, st7789.WHITE)

def clear_color_circle(color):
    if color <= 6:
        tft.fill_circle(25, 49 + (13 * color), 4, st7789.BLACK)
    else:
        tft.fill_circle(109, 49 + (13 * (color - 7)), 4, st7789.BLACK)

# 定义短按center按钮的回调函数
def center_button_short_press_callback():
    global led_state
    if led_state:
        enable_pin.value(1)# 设置低电平，接通电源输出
    else:
        enable_pin.value(0)# 设置高阻态，关断电源输出
        
    led_state = not led_state  # 切换LED的状态
        

# 定义长按center按钮的回调函数
def center_button_long_press_callback():
    global exit_program
    exit_program = True  # 设置退出标志位

# 注册按钮回调函数
buttons.register_callback('left', 'short', left_button_short_press_callback)
buttons.register_callback('right', 'short', right_button_short_press_callback)
buttons.register_callback('up', 'short', up_button_short_press_callback)
buttons.register_callback('up', 'long', up_button_long_press_callback)
buttons.register_callback('down', 'short', down_button_short_press_callback)
buttons.register_callback('center', 'short', center_button_short_press_callback)
buttons.register_callback('center', 'long', center_button_long_press_callback)

# 绘制初始的中心圆
tft.fill_circle(tft.width() // 2, (tft.height() // 2) - 30, 25, colors[0])
tft.fill_circle(41+(13*brightness), 25, 4, st7789.WHITE)
show_color_circle(color)

while not exit_program:  # 只有当exit_program为False时才继续循环
    if led_state:  # 只有当LED打开时才进行光效更新
        current_color = color  # 记录当前的颜色

        if color == 12:  # 固定的彩虹色
            fixed_rainbow_colors = [
                (255, 0, 0),      # 红色
                (255, 127, 0),    # 橙色
                (255, 255, 0),    # 黄色
                (0, 255, 0),      # 绿色
                (0, 0, 255),      # 蓝色
                (75, 0, 130),     # 靛色
                (148, 0, 211)     # 紫色
            ]
            
            num_colors = len(fixed_rainbow_colors)
            for i in range(MAX_RESOLUTION):
                color_index = i * num_colors // MAX_RESOLUTION
                r, g, b = fixed_rainbow_colors[color_index]
                brightness_factor = max(brightness / 4, MIN_BRIGHTNESS_FACTOR)
                adjusted_color = (int(r * brightness_factor), int(g * brightness_factor), int(b * brightness_factor))
                
                # 根据 interval_mode 来决定是否间隔亮
                if interval_mode:
                    if i % 2 == 0:  # 偶数灯亮
                        np[i] = adjusted_color
                    else:           # 奇数灯灭
                        np[i] = (0, 0, 0)
                else:
                    np[i] = adjusted_color  # 不间隔亮，全部亮
            np.write()
            time.sleep(0.1)

        elif color == 13:  # 整体渐变彩虹效果
            for i in range(256):
                if color != current_color or not led_state or exit_program:  # 检查颜色是否改变、LED状态是否变化或是否退出
                    break
                r, g, b = wheel(i & 255)
                brightness_factor = max(brightness / 4, MIN_BRIGHTNESS_FACTOR)
                adjusted_color = (int(r * brightness_factor), int(g * brightness_factor), int(b * brightness_factor))

                # 根据 interval_mode 来决定是否间隔亮
                for j in range(MAX_RESOLUTION):
                    if interval_mode:
                        if j % 2 == 0:  # 偶数灯亮
                            np[j] = adjusted_color
                        else:           # 奇数灯灭
                            np[j] = (0, 0, 0)
                    else:
                        np[j] = adjusted_color  # 不间隔亮，全部亮
                np.write()
                time.sleep(0.001)  # 渐变速度

        else:
            adjusted_color = apply_brightness(colors[color], brightness)
            r = adjusted_color >> 11
            g = (adjusted_color >> 5) & 0x3F
            b = adjusted_color & 0x1F
            rgb = (int(r * 255 / 31), int(g * 255 / 63), int(b * 255 / 31))
            
            # 根据 interval_mode 来决定是否间隔亮
            for i in range(MAX_RESOLUTION):
                if interval_mode:
                    if i % 2 == 0:  # 偶数灯亮
                        np[i] = rgb
                    else:           # 奇数灯灭
                        np[i] = (0, 0, 0)
                else:
                    np[i] = rgb  # 不间隔亮，全部亮
            np.write()
            time.sleep(0.1)
    else:
        np.fill((0, 0, 0))  # 关闭LED
        np.write()
        time.sleep(0.1)  # 如果LED关闭，稍微休眠以节省资源



# 清理操作，例如关闭LED或其他资源释放
np.fill((0, 0, 0))  # 确保LED关闭
np.write()
enable_pin.value(1)# 设置高阻态，关断电源输出
buttons.deinit()
tft.fill(st7789.BLACK)  # 清除屏幕
gc.collect()
