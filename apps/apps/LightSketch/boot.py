import sys
import LightSketch

# 检查模块是否在 sys.modules 中
if 'LightSketch' in sys.modules:
    del sys.modules['LightSketch']
    print("模块 'LightSketch' 已从 sys.modules 中删除")
else:
    print("模块 'LightSketch' 不在 sys.modules 中")
