# 追书精细化算法与快速反馈链路

本文针对黄色封面书本目标，例如 `Big meets Little` 这类高饱和黄封面、矩形边界清楚的桌面书，说明当前 repo 的推荐算法设置。

## 核心策略

第一版不要上复杂模型。最稳的链路是：

```text
黄色封面颜色锁定
  + 矩形/边缘/填充率确认
  + 运动只作为加分项
  -> 输出书本中心点
  -> bridge 高频转发
  -> runtime 小步低头跟随
```

颜色锁定是主信号，边缘和形状用于排除桌面纹理，运动用于提升移动时的置信度。这样书停住以后也能继续被锁定，不会因为没有 motion 而丢失。

## 已落地的 detector

`scripts/track_target_event_extractor.py` 已增加黄色书封面 detector：

```text
detector: book_cover_color
target_class: book
target_subclass: yellow_book
target_mode: tabletop_follow
```

默认 OpenCV HSV 范围：

```text
H: 14-43
S: >= 70
V: >= 80
```

推荐环境变量：

```bash
export MIRA_LIGHT_DEFAULT_TARGET_MODE=tabletop_follow
export MIRA_LIGHT_TABLETOP_ROI_TOP=0.16
export MIRA_LIGHT_TABLETOP_ROI_BOTTOM=0.96
export MIRA_LIGHT_TABLETOP_ROI_LEFT=0.08
export MIRA_LIGHT_TABLETOP_ROI_RIGHT=0.92
export MIRA_LIGHT_TABLETOP_MAX_AREA_RATIO=0.65
export MIRA_LIGHT_TABLETOP_BOOK_HUE_MIN=14
export MIRA_LIGHT_TABLETOP_BOOK_HUE_MAX=43
export MIRA_LIGHT_TABLETOP_BOOK_MIN_SATURATION=70
export MIRA_LIGHT_TABLETOP_BOOK_MIN_VALUE=80
export MIRA_LIGHT_TABLETOP_BOOK_MIN_COLOR_RATIO=0.22
export MIRA_LIGHT_TABLETOP_TRACKING_UPDATE_MS=110
```

## 反馈链路

推荐频率：

```text
摄像头推帧: 8-12 fps
extractor poll: 0.10-0.20s
bridge tabletop update: 110ms
runtime servo step: 每次 yaw 最多 6 度，pitch 最多 4 度
```

runtime 对 `tabletop_follow` 使用单独映射：

```text
servo1: 主要左右跟随书本中心
servo2: 保持稳定桌面低头姿态
servo3: 保持轻微前探，不频繁伸缩
servo4: 小幅调灯头俯仰，让光落在书附近
LED: 功能性白光
```

deadband：

```text
yaw:   0.035
pitch: 0.060
```

这个 deadband 能避免书本中心在图像中抖 1-2 个像素时舵机跟着抖。

## 现场调参顺序

1. 先固定摄像头，确认 `vision.latest.json` 中 `detector == book_cover_color`。
2. 移动书到左、中、右三处，观察 `center_norm.x` 是否连续变化。
3. 如果检测不到黄色封面，先降低 `MIRA_LIGHT_TABLETOP_BOOK_MIN_SATURATION` 到 `55`。
4. 如果把木桌误识别成书，提高 `MIRA_LIGHT_TABLETOP_BOOK_MIN_COLOR_RATIO` 到 `0.30`。
5. 如果跟随慢，降低 `MIRA_LIGHT_TABLETOP_TRACKING_UPDATE_MS` 到 `90`。
6. 如果灯头抖，提高 deadband 或降低摄像头帧率到 `8 fps`。

## 判断链路是否健康

`vision.latest.json` 应出现：

```json
{
  "tracking": {
    "target_class": "book",
    "target_subclass": "yellow_book",
    "target_mode": "tabletop_follow",
    "detector": "book_cover_color"
  },
  "control_hint": {
    "feedback_profile": "tabletop_book",
    "recommended_update_ms": 110
  }
}
```

`vision.bridge.state.json` 应出现：

```json
{
  "lastDecision": {
    "action": "apply_tracking"
  }
}
```

runtime 状态应出现：

```json
{
  "trackingActive": true,
  "trackingTarget": {
    "trackingProfile": "tabletop_book",
    "detector": "book_cover_color"
  }
}
```
