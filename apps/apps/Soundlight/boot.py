import mic
import time
from machine import Pin
import vga2_8x16 as font_8x16
import vga2_16x32 as font_16x32
from button import Button
import neopixel
import gc
import tft_config
import st7789

# ---------- 参数配置 ----------
SAMPLE_RATE = 16000   # 采样率
BIT_WIDTH = 16        # 位宽
CHANNELS = 1          # 通道数（1 = mono）
BUFF_SIZE = 1024      # 每次读取的缓冲区大小
# 初始化 I2S PDM
mic.init(SAMPLE_RATE, BIT_WIDTH, CHANNELS, BUFF_SIZE)

# 创建LCD对象
tft = tft_config.config(0)
tft.init()
tft.jpg('/sd/apps/Soundlight/jiezhou.jpg', 0, 0, st7789.SLOW)

# 定义按钮对象
buttons = Button()

# 电源使能引脚
enable_pin = Pin(43, Pin.OPEN_DRAIN) # 电源使能引脚，根据实际情况选择正确的引脚
enable_pin.value(0)# 设置低，接通电源输出

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

exit_program = False  # 退出标志位

# 初始化变量，分别代表亮度、灵敏度和模式
brightness = 5  # 可以调节此值来控制亮度
sensitivity = 5  # 灵敏度调节参数
display_mode = 0  # 模式选择变量，0 为线性点亮，1 为从中间向两边跳动

# 初始化 LED 状态缓冲区
led_states = [(0, 0, 0)] * NUM_PIXELS

# 允许的最大减少量，控制逐渐减少的步伐
DECREASE_STEP = 10

# 设定静音阈值
MUTE_THRESHOLD = 20  # 根据实际情况调整阈值

# 文件保存路径
save_file = '/sd/apps/Soundlight/values.txt'

# 当前选项指针位置
pointer_position = 0
previous_position = None  # 初始化前一个位置变量

# 从文件加载值
def load_values():
    global brightness, sensitivity, display_mode
    try:
        with open(save_file, 'r') as f:
            lines = f.readlines()
            brightness = int(lines[0].strip()) if len(lines) > 1 else 5
            sensitivity = int(lines[1].strip()) if len(lines) > 1 else 5
            display_mode = int(lines[2].strip()) if len(lines) > 2 else 0
    except OSError:
        print("Save file not found, using default values.")
        brightness = 5
        sensitivity = 5
        display_mode = 0

# 保存值到文件
def save_values():
    with open(save_file, 'w') as f:
        f.write(f"{brightness}\n")
        f.write(f"{sensitivity}\n")
        f.write(f"{display_mode}\n")

# 加载文件中的初始值
load_values()

# 绘制界面
def draw_interface():
    global previous_position
    # 清除上一个圆点
    if previous_position is not None and previous_position != pointer_position:
        tft.fill_circle(10, 38 + previous_position * 42, 5, st7789.BLACK)

    # 更新选项显示
    for i in range(3):
        # 当前选中项加上小圆点
        if i == pointer_position:
            tft.fill_circle(10, 38 + i * 42, 5, st7789.RED)

        # 绘制更新的文本
        if i == 0:
            brightness_text = "{:<2}".format(brightness)
            tft.text(font_8x16, brightness_text, 100, 32 + i * 42, st7789.YELLOW, st7789.BLACK)
        elif i == 1:
            sensitivity_text = "{:<2}".format(sensitivity)
            tft.text(font_8x16, sensitivity_text, 100, 32 + i * 42, st7789.YELLOW, st7789.BLACK)
        else:
            display_mode_text = "{:<2}".format(display_mode)
            tft.text(font_8x16, display_mode_text, 100, 32 + i * 42, st7789.YELLOW, st7789.BLACK)

    # 更新上一个指针位置
    previous_position = pointer_position

# 按钮回调函数
def up_button_callback():
    global pointer_position
    if pointer_position > 0:
        pointer_position -= 1
        draw_interface()

def down_button_callback():
    global pointer_position
    if pointer_position < 2:  # 有三个选项
        pointer_position += 1
        draw_interface()

def left_button_callback():
    global brightness, sensitivity, display_mode
    if pointer_position == 0:
        brightness -= 1
        if brightness < 1: brightness = 1  # 限制亮度最小值
    elif pointer_position == 1:
        sensitivity -= 1
        if sensitivity < 1: sensitivity = 1  # 限制灵敏度最小值
    elif pointer_position == 2:
        display_mode -= 1
        if display_mode < 0: display_mode = 0  # 限制模式最小值
    save_values()
    draw_interface()

def right_button_callback():
    global brightness, sensitivity, display_mode
    if pointer_position == 0:
        brightness += 1
        if brightness > 10: brightness = 10  # 限制亮度最大值
    elif pointer_position == 1:
        sensitivity += 1
        if sensitivity > 10: sensitivity = 10  # 限制灵敏度最大值
    elif pointer_position == 2:
        display_mode += 1
        if display_mode > 1: display_mode = 1  # 限制模式最大值
    save_values()
    draw_interface()

# 定义长按center按钮的回调函数
def center_button_long_press_callback():
    global exit_program
    exit_program = True  # 设置退出标志位

# 注册按钮回调
buttons.register_callback('up', 'short', up_button_callback)
buttons.register_callback('down', 'short', down_button_callback)
buttons.register_callback('left', 'short', left_button_callback)
buttons.register_callback('right', 'short', right_button_callback)
buttons.register_callback('center', 'long', center_button_long_press_callback)

draw_interface()

def calculate_volume_level(max_value):
    # 将最大值转换为音量级别
    max_amplitude = 1000  # 假设最大振幅为32767
    volume_level = int((max_value / max_amplitude) * 100 * sensitivity / 5)  # 增加灵敏度影响

    # 如果音量低于静音阈值，将其设置为0
    if volume_level < MUTE_THRESHOLD:
        volume_level = 0

    return min(max(volume_level, 0), 100)



# 为整个灯珠长度生成一个完整的彩虹梯度
def generate_rainbow_colors(num_pixels):
    colors = []
    for i in range(num_pixels):
        position = i / num_pixels
        # 彩虹梯度生成公式
        if position < 1/3:  # 红到黄
            r = 255
            g = int(255 * (position * 3))
            b = 0
        elif position < 2/3:  # 黄到绿
            r = int(255 * (2 - position * 3))
            g = 255
            b = 0
        else:  # 绿到蓝
            r = 0
            g = int(255 * (3 - position * 3))
            b = 255
        colors.append((r, g, b))

    # 将最大的亮灯位置（即最后一个灯）设为白色
    if num_pixels > 0:
        colors[-1] = (255, 255, 255)  # 最大亮灯位置设置为白色

    return colors

# 为灯珠生成一个从中央对称展开的彩虹梯度，且两端为白色
def generate_symmetric_rainbow_colors(num_pixels):
    if num_pixels <= 0:
        return []

    # 中心点位置
    center = num_pixels // 2

    # 初始化颜色列表
    colors = [None] * num_pixels

    def calculate_color(position):
        """根据位置计算彩虹颜色"""
        if position < 1/3:  # 红到黄
            r = 255
            g = int(255 * (position * 3))
            b = 0
        elif position < 2/3:  # 黄到绿
            r = int(255 * (2 - position * 3))
            g = 255
            b = 0
        else:  # 绿到蓝
            r = 0
            g = int(255 * (3 - position * 3))
            b = 255
        return (r, g, b)

    # 为中心到边界生成彩虹颜色
    for i in range(center + 1):
        if i == center:  # 在中心点两端加入白色
            color = (255, 255, 255)
        else:
            position = i / (center if center > 0 else 1)  # 防止除以零
            color = calculate_color(position)

        # 确保索引不越界
        if center + i < num_pixels:
            colors[center + i] = color  # 中心向右
        if center - i >= 0:
            colors[center - i] = color  # 中心向左

    # 处理两端为白色
    if num_pixels % 2 == 0:
        colors[0] = (255, 255, 255)  # 左端白色
        colors[num_pixels - 1] = (255, 255, 255)  # 右端白色

    return colors

# 为 144 颗灯珠生成彩虹颜色
FIXED_COLORS = generate_symmetric_rainbow_colors(NUM_PIXELS)

# 初始化变量来记录上一个音量对应的亮灯数量
previous_num_lit = 0

# 新增一个变量来记录最大亮灯数量
max_lit = 0

# 增加一个变量记录上次的 display_mode
last_display_mode = None

# 更新 FIXED_COLORS 根据当前的显示模式
def update_colors_based_on_mode():
    global FIXED_COLORS
    if display_mode == 0:  # 线性模式
        FIXED_COLORS = generate_rainbow_colors(NUM_PIXELS)
    elif display_mode == 1:  # 对称模式
        FIXED_COLORS = generate_symmetric_rainbow_colors(NUM_PIXELS)

def update_leds(volume_level):
    global previous_num_lit  # 使用全局变量，记录上一个音量的亮灯数量
    global max_lit  # 使用全局变量，记录最大亮灯数
    global last_display_mode  # 使用全局变量，记录上次的 display_mode

    # 检查显示模式是否发生变化，若发生变化则更新颜色
    if display_mode != last_display_mode:
        update_colors_based_on_mode()
        last_display_mode = display_mode  # 更新上次模式

    # 根据音量计算当前应该点亮的灯珠数量
    current_num_lit = int((volume_level / 100) * NUM_PIXELS)

    # 如果当前亮灯数量少于上一次，逐渐减少亮灯数量
    if current_num_lit < previous_num_lit:
        num_lit = max(previous_num_lit - DECREASE_STEP, current_num_lit)
    else:
        num_lit = current_num_lit

    # 更新最大亮灯数
    if num_lit > max_lit:
        max_lit = num_lit

    # 如果当前模式是线性点亮
    if display_mode == 0:
        # 如果最大亮灯数没有被更新，则逐渐减少它
        if num_lit < max_lit:
            max_lit -= 1

        for i in range(NUM_PIXELS):
            if i < num_lit:
                r, g, b = FIXED_COLORS[i]
                r = int(r * (brightness * 0.1))
                g = int(g * (brightness * 0.1))
                b = int(b * (brightness * 0.1))
                np[i] = (r, g, b)
            else:
                np[i] = (0, 0, 0)

        # 在最大亮灯处显示白色，并应用亮度调节，`max_lit` 为零时熄灭白灯
        if max_lit > 0 and max_lit < NUM_PIXELS:
            white_brightness = int(255 * (brightness * 0.1))  # 根据亮度调整白色的亮度
            np[max_lit] = (white_brightness, white_brightness, white_brightness)

    # 如果当前模式是从中间向两边跳动
    elif display_mode == 1:
        center_index = NUM_PIXELS // 2  # 中心位置
        half_num_lit = num_lit // 2  # 每侧点亮的灯珠数量

        if center_index < max_lit:
            max_lit -= 1

        for i in range(NUM_PIXELS):
            np[i] = (0, 0, 0)  # 清空灯珠显示

        for i in range(half_num_lit):
            # 左侧（从中心向左）
            if center_index - i - 1 >= 0:
                r, g, b = FIXED_COLORS[center_index - i - 1]
                r = int(r * (brightness * 0.1))
                g = int(g * (brightness * 0.1))
                b = int(b * (brightness * 0.1))
                np[center_index - i - 1] = (r, g, b)

            # 右侧（从中心向右）
            if center_index + i < NUM_PIXELS:
                r, g, b = FIXED_COLORS[center_index + i]
                r = int(r * (brightness * 0.1))
                g = int(g * (brightness * 0.1))
                b = int(b * (brightness * 0.1))
                np[center_index + i] = (r, g, b)

        # 在最大亮灯处显示白色，并应用亮度调节，`max_lit` 为零时熄灭白灯
        if max_lit > center_index and max_lit < NUM_PIXELS:
            white_brightness = int(255 * (brightness * 0.1))  # 根据亮度调整白色的亮度
            np[max_lit] = (white_brightness, white_brightness, white_brightness)
            np[center_index - (max_lit - center_index)] = (white_brightness, white_brightness, white_brightness)

    # 写入灯珠状态
    np.write()

    # 更新记录的亮灯数量
    previous_num_lit = num_lit

# 主循环
try:
    while not exit_program:
        # 从代码A中获取最大值
        stats = mic.calculate_stats()
        if stats:
            max_value = stats['max']
            volume_level = calculate_volume_level(max_value)
            update_leds(volume_level)
        else:
            print("Failed to read data")

        # 延迟一段时间（例如 200ms）
        #time.sleep_ms(200)

        gc.collect()
except KeyboardInterrupt:
    print("Recording stopped")
finally:
    print("Program stopped")

np.fill((0, 0, 0))  # 确保LED关闭
np.write()
enable_pin.value(1)# 设置高阻态，关断电源输出
buttons.deinit()
tft.fill(st7789.BLACK)  # 清除屏幕
gc.collect()

# 释放 I2S PDM 资源
mic.release()


