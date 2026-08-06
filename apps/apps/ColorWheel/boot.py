from machine import Pin
import vga2_8x16 as font_8x16
import vga2_16x32 as font_16x32
from button import Button
import neopixel
import time
import gc
def hsl_to_rgb(h, s, l):
    """
    Convert HSL to RGB.
    h: Hue (0-360)
    s: Saturation (0-100)
    l: Lightness (0.05-0.5)
    Returns a tuple of (r, g, b) with each component in the range 0-255.
    """
    s /= 100  # Scale saturation to 0.0-1.0
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l - c / 2

    if 0 <= h < 60:
        r, g, b = c, x, 0
    elif 60 <= h < 120:
        r, g, b = x, c, 0
    elif 120 <= h < 180:
        r, g, b = 0, c, x
    elif 180 <= h < 240:
        r, g, b = 0, x, c
    elif 240 <= h < 300:
        r, g, b = x, 0, c
    elif 300 <= h < 360:
        r, g, b = c, 0, x
    else:
        r, g, b = 0, 0, 0

    r = int((r + m) * 255)
    g = int((g + m) * 255)
    b = int((b + m) * 255)

    return r, g, b

import tft_config
import st7789
tft = tft_config.config(0)
tft.init()

tft.jpg('/sd/apps/ColorWheel/colorwheel.jpg', 0, 0, st7789.SLOW)
# 定义按钮对象
buttons = Button()

# 电源使能引脚
enable_pin = Pin(43, Pin.OPEN_DRAIN) # 电源使能引脚，根据实际情况选择正确的引脚
enable_pin.value(1)# 设置高阻态，关断电源输出

import pm
pm.init()
pm.set_power_state(pm.VCC_OUTPUT)

# 设置 RGB LED
NUM_PIXELS = 144
try:
    import ujson
    with open('/sd/apps/config.json', 'r') as f:
        config = ujson.loads(f.read())
        light_stick_length = config.get('light_stick_length', 3)
        NUM_PIXELS = light_stick_length * 48
        print(f"Loaded light_stick_length: {light_stick_length}, NUM_PIXELS: {NUM_PIXELS}")
except Exception as e:
    print(f"Failed to load config, using default NUM_PIXELS=144: {e}")

np = neopixel.NeoPixel(Pin(13), NUM_PIXELS)






# 点亮 142 颗灯，统一控制颜色
saturation = 100  # 饱和度，范围 1-100
current_level = 50  # 亮度百分比，范围 0-100
hue = 0  # 色相，初始值为 0

led_state = False  # 初始化LED状态为开
exit_program = False  # 退出标志位

# 绘制中心圆
center_x = tft.width() // 2
center_y = tft.height() // 2
radius = 30

def convert_rgb_to_565(r, g, b):
    """Convert RGB values (0-255) to 16-bit color format (RGB565)."""
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

# 初始化指针位置和亮度等级
pointer_position = 0
previous_position = None  # 初始化前一个位置变量

def get_mapped_brightness(level):
    """映射亮度百分比 (0-100%) 到实际亮度范围 (0.05-0.5)."""
    return 0.05 + (level / 100) * (0.5 - 0.05)


# 文件保存路径
save_file = '/sd/apps/ColorWheel/values.txt'

# 从文件加载值
def load_values():
    global saturation, current_level, hue
    try:
        with open(save_file, 'r') as f:
            lines = f.readlines()
            saturation = int(lines[0].strip()) if len(lines) > 1 else 100
            current_level = int(lines[1].strip()) if len(lines) > 1 else 50
            hue = int(lines[2].strip()) if len(lines) > 1 else 0
    except OSError:
        print("Save file not found, using default values.")
        saturation = 100  
        current_level = 50  
        hue = 0  

# 保存值到文件
def save_values():
    with open(save_file, 'w') as f:
        f.write(f"{saturation}\n")
        f.write(f"{current_level}\n")
        f.write(f"{hue}\n")

# 加载文件中的初始值
load_values()



# 绘制界面
def draw_interface():
    global previous_position

    # 清除上一个圆点
    if previous_position is not None and previous_position != pointer_position:
        tft.fill_circle(14, 23 + previous_position * 22, 5, st7789.BLACK)

    # 更新选项显示
    for i in range(3):
        # 当前选中项加上小圆点
        if i == pointer_position:
            tft.fill_circle(14, 23 + i * 22, 5, st7789.RED)

        # 绘制更新的文本
        if i == 0:
            hue_text = "{:>3}".format(hue) 
            tft.text(font_8x16, hue_text, 100, 18 + i * 22, st7789.YELLOW, st7789.BLACK)
        elif i == 1:
            saturation_text = "{:>3}%".format(saturation) 
            tft.text(font_8x16, saturation_text, 100, 18 + i * 22, st7789.YELLOW, st7789.BLACK)
        else:
            current_level_text = "{:>3}%".format(current_level) 
            tft.text(font_8x16, current_level_text, 100, 18 + i * 22, st7789.YELLOW, st7789.BLACK)

    # 更新屏幕上的圆颜色
    lightness = get_mapped_brightness(current_level)
    r, g, b = hsl_to_rgb(hue, saturation, lightness)
    color_565 = convert_rgb_to_565(r, g, b)
    tft.fill_circle(center_x, center_y, radius, color_565)

    # 更新上一个指针位置
    previous_position = pointer_position

draw_interface()

# 按键回调函数
def up_button_callback():
    global pointer_position
    if pointer_position > 0:
        pointer_position -= 1
        draw_interface()

def down_button_callback():
    global pointer_position
    if pointer_position < 2:  # 三个选项
        pointer_position += 1
        draw_interface()

def left_button_callback():
    global current_level, saturation, hue
    if pointer_position == 2:  # 调节亮度
        current_level = max(0, current_level - 1)  # 减少 1%
    elif pointer_position == 1:  # 调节饱和度
        saturation = max(1, saturation - 1)  # 饱和度减少 1%
    elif pointer_position == 0:  # 调节色相
        hue = (hue - 1) % 360
    draw_interface()

def right_button_callback():
    global current_level, saturation, hue
    if pointer_position == 2:  # 调节亮度
        current_level = min(100, current_level + 1)  # 增加 1%
    elif pointer_position == 1:  # 调节饱和度
        saturation = min(100, saturation + 1)  # 饱和度增加 1%
    elif pointer_position == 0:  # 调节色相
        hue = (hue + 1) % 360
    draw_interface()

def center_button_callback():
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


# 注册按键回调
buttons.register_callback('up', 'short', up_button_callback)
buttons.register_callback('down', 'short', down_button_callback)
#buttons.register_callback('left', 'short', left_button_callback)
#buttons.register_callback('right', 'short', right_button_callback)
buttons.register_callback('center', 'short', center_button_callback)
buttons.register_callback('center', 'long', center_button_long_press_callback)


left_button_was_pressed = False
right_button_was_pressed = False


# 主循环
try:
    while not exit_program:
        if buttons.get_button_state('left'):
            left_button_callback()
            left_button_was_pressed = True
        elif left_button_was_pressed == True:
            left_button_was_pressed = False
            save_values()

        if buttons.get_button_state('right'):
            right_button_callback()
            right_button_was_pressed = True
        elif right_button_was_pressed == True:
            right_button_was_pressed = False
            save_values()

                
        
        
        if led_state:  # 只有当LED打开时才进行光效更新
        
            lightness = get_mapped_brightness(current_level)  # 使用当前亮度等级
            r, g, b = hsl_to_rgb(hue, saturation, lightness)

            # 更新 LED 灯光
            for i in range(NUM_PIXELS):
                np[i] = (r, g, b)
            np.write()
        else:
            np.fill((0, 0, 0))  # 关闭LED
            np.write()
except KeyboardInterrupt:
    print("Recording stopped")
finally:
    print("out")

# 清理操作，例如关闭LED或其他资源释放
np.fill((0, 0, 0))  # 确保LED关闭
np.write()
enable_pin.value(1)# 设置高阻态，关断电源输出
buttons.deinit()
tft.fill(st7789.BLACK)  # 清除屏幕
gc.collect()

