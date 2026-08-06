# 萤火虫T1 官方应用库 · Firefly T1 App Library

[官方网站](https://socolode.com) · [文档中心](https://docs.socolode.com) · [社区交流](https://github.com/socolode/docs/blob/main/i18n/zh-CN/docusaurus-plugin-content-docs/current/light-painting-controller/help-community/community-contact.mdx)

> 本仓库集中存放 **萤火虫T1 灯光控制器** 的官方与社区应用（App）。无需编程，下载即用，持续更新。

---

## 快速开始

1. 打开 [应用列表](#应用列表)，挑选你喜欢的应用
2. 点击对应行的「下载」获取压缩包，解压到本地
3. 把解压后的文件夹复制到萤火虫T1 U 盘的 `/apps` 目录中
4. 编辑 `apps/config.json`，在 `apps` 数组中加入新应用信息（参考下方模板）
5. 重启设备，左右拨动摇杆切换到该应用，单击中键启动

> 完整图文安装步骤见文档：[**萤火虫T1 · 应用安装**](https://docs.socolode.com/zh-CN/light-painting-controller/firefly-t1/apps-play/app-list-install)

### config.json 填写模板

```json
{
  "apps": [
    {
      "name": "时光环",
      "folder": "time-ring",
      "enabled": true
    },
    {
      "name": "光绘",
      "folder": "light-painting",
      "enabled": true
    }
  ]
}
```

---

## 应用列表

| 应用名称 | 说明 | 适用场景 | 作者 | 下载 |
|---------|------|---------|------|------|
| 光绘 Light Painting | 长曝光摄影光绘，自定义字符 / 图案 / 渐变 | 光绘摄影、夜景人像 | socolode | 稍后开放 |
| 时光环 Time Ring | 手持灯环绘制时钟图案 / 光绘圆环 | 创意摄影、静物布景 | socolode | 稍后开放 |
| 桌面节奏灯 Rhythm Light | 音频频率响应，灯光随音乐律动 | 桌面氛围、派对 | socolode | 稍后开放 |
| 兼容灯材接线示例 | WS2812 / SK6812 RGBW / 灯环 / 矩阵的接线参考图 | 入门搭建、硬件接线 | socolode | 稍后开放 |
| 3D 打印外壳文件 | 萤火虫T1 主机、时光环、节奏灯的 STL 模型 | 定制外壳 | socolode | 稍后开放 |
| WLED 集成（开发中）| 接入 WLED 开源生态：网页 UI / 预设 / 智能家居（Home Assistant / Alexa） | 氛围灯、智能家装 | socolode | 开发中 |

> 更多应用正在陆续上传中。若应用库暂无你需要的效果，欢迎到社区反馈需求，或参考进阶开发章节自行编写。

---

## 目录结构（每个应用）

每个应用文件夹建议遵循以下结构：

```
my-app/
├── main.py            # 应用入口脚本（必选）
├── config.json        # 应用默认参数（可选）
├── assets/            # 图片、字体、BMP 素材（可选）
│   └── logo.bmp
├── README.md          # 应用说明（接线、参数、效果演示，推荐）
└── preview.png        # 效果预览图，用于应用库展示（推荐）
```

---

## 贡献你的应用（PR 欢迎）

本仓库欢迎社区开发者提交应用，步骤如下：

1. **Fork** 本仓库
2. 在 `apps/` 目录下新建一个以你的应用名称命名的文件夹，按上述结构放置文件
3. 编辑上方的「应用列表」表格，添加一行说明
4. 发起 **Pull Request**，等待审核合并

### 贡献建议

- README.md 中必须包含：接线说明、参数说明、效果展示（图片或视频链接）
- 如使用第三方素材，确保版权允许分发
- 推荐在应用说明里附上设备与灯材型号，方便他人复现

### 进阶开发

- 搭建开发环境、编写第一个应用、打包与分享教程：
  👉 [萤火虫T1 · 进阶开发](https://docs.socolode.com/zh-CN/light-painting-controller/app-development/setup-environment)

---

## 相关链接

- 产品官网：[socolode.com](https://socolode.com)
- 文档中心：[docs.socolode.com](https://docs.socolode.com)
- 主仓库（文档与网站源码）：[socolode/docs](https://github.com/socolode/docs)
- 社区与联系方式：[帮助与社区](https://docs.socolode.com/zh-CN/light-painting-controller/help-community/community-contact)
- 提交 Bug / 功能建议：[Issues](https://github.com/socolode/firefly-t1-apps/issues)

---

## License

- 本仓库中的代码与应用按 **MIT License** 发布（见 [LICENSE](./LICENSE)）
- 第三方素材版权归其原作者所有，详见各应用目录中的说明