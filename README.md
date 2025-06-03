# SRF圖像格式轉換器 - Python工具包

這是一個用於Garmin SRF（Scalable Raster Format）圖像格式轉換的Python工具包，提供雙向轉換功能。

## 原始來源
https://github.com/jgreer/srf_converter.git

## 工具概覽

本工具包包含兩個主要轉換器：

1. **srf2png.py** - 將SRF格式轉換為PNG格式
2. **png2srf.py** - 將PNG格式轉換為SRF格式

## 功能特色

### SRF到PNG轉換器 (srf2png.py)
- 將SRF格式轉換為PNG格式
- 支援分離的alpha遮罩輸出
- 自動生成包含圖像資訊的文字檔案
- 支援多個圖像段的SRF檔案
- 檔案覆蓋保護機制

### PNG到SRF轉換器 (png2srf.py)
- 將PNG格式轉換回SRF格式
- 支援分離遮罩的重建
- 從資訊檔案重建多段圖像結構
- 完整的圖像資料還原

## 系統需求

- Python 3.6 或更新版本
- macOS、Linux、Windows（跨平台支援）
- Pillow圖像處理函式庫

## 安裝方法

1. 確保您的系統已安裝Python 3：
   ```bash
   python3 --version
   ```

2. 安裝必要的依賴項：
   ```bash
   pip3 install -r requirements.txt
   ```

   或手動安裝Pillow：
   ```bash
   pip3 install Pillow
   ```

## 使用方法

### SRF到PNG轉換器 (srf2png.py)

#### 基本語法
```bash
python3 srf2png.py [選項] <SRF檔案名> <PNG基礎名>
```

#### 選項說明
- `-m`: 使用分離的alpha遮罩圖像
- `-f`: 強制覆蓋現有檔案
- `-h`: 顯示幫助訊息

#### 使用範例

1. **基本轉換**：
   ```bash
   python3 srf2png.py vehicle.srf output
   ```
   輸出檔案：
   - `output.png`（包含RGBA通道）
   - `output_info.txt`（圖像資訊）

2. **使用分離遮罩**：
   ```bash
   python3 srf2png.py -m vehicle.srf output
   ```
   輸出檔案：
   - `output.png`（RGB圖像）
   - `output_mask.png`（灰階遮罩）
   - `output_info.txt`（圖像資訊）

3. **強制覆蓋現有檔案**：
   ```bash
   python3 srf2png.py -f vehicle.srf output
   ```

### PNG到SRF轉換器 (png2srf.py)

#### 基本語法
```bash
python3 png2srf.py [選項] <PNG基礎名> <SRF檔案名>
```

#### 選項說明
- `-f`: 強制覆蓋現有檔案
- `-h`: 顯示幫助訊息

#### 使用範例

1. **基本轉換**（從RGBA PNG）：
   ```bash
   python3 png2srf.py output vehicle_converted.srf
   ```
   需要的輸入檔案：
   - `output.png`（RGBA格式PNG）
   - `output_info.txt`（圖像資訊）

2. **分離遮罩轉換**：
   ```bash
   python3 png2srf.py output vehicle_converted.srf
   ```
   需要的輸入檔案：
   - `output.png`（RGB格式PNG）
   - `output_mask.png`（遮罩PNG）
   - `output_info.txt`（圖像資訊）

3. **強制覆蓋現有檔案**：
   ```bash
   python3 png2srf.py -f output vehicle_converted.srf
   ```

## 完整轉換流程範例

### 從SRF到PNG再回到SRF
```bash
# 步驟1: 將SRF轉換為PNG（使用分離遮罩）
python3 srf2png.py -m original.srf temp

# 步驟2: 將PNG轉換回SRF
python3 png2srf.py temp converted.srf

# 驗證: 比較原始檔案和轉換後檔案
python3 srf2png.py original.srf original_check
python3 srf2png.py converted.srf converted_check
```

## 檔案格式說明

### SRF檔案格式
SRF是Garmin使用的一種點陣圖格式，包含：
- 檔案標頭（包含版本和產品資訊）
- 多個圖像段
- 每個段包含尺寸、RGB資料和alpha資料

### 轉換輸出檔案

#### SRF到PNG轉換輸出

1. **PNG圖像檔案**：
   - 無分離遮罩：RGBA格式的PNG檔案
   - 有分離遮罩：RGB格式的PNG檔案

2. **遮罩檔案**（僅在使用-m選項時）：
   - 灰階PNG檔案，表示透明度資訊

3. **資訊檔案**：
   - 文字檔案，包含圖像尺寸、段數等重建SRF所需的資訊

#### PNG到SRF轉換需要的輸入檔案

1. **主要PNG檔案**：包含圖像的RGB或RGBA資料
2. **遮罩檔案**（選用）：分離的alpha通道資料
3. **資訊檔案**：包含原始SRF結構資訊（必需）

### 資訊檔案格式範例
```
Width: 64
Height: 64
SectionCount: 1
SectionWidth1: 64
SectionHeight1: 64
MaskFile: output_mask.png
```

## 技術實作說明

### 主要類別和方法

#### Srf2Png類別
- `convert()`: 主要轉換方法
- `_process_srf_file()`: 處理SRF檔案結構
- `_read_image_section()`: 讀取個別圖像段
- `_decode_color()`: 16位色彩轉24位色彩
- `_decode_alpha()`: alpha通道解碼

#### Png2Srf類別
- `convert()`: 主要轉換方法
- `_write_srf_file()`: 寫入SRF檔案
- `_write_image_section()`: 寫入個別圖像段
- `_encode_color()`: 24位色彩轉16位色彩
- `_encode_alpha()`: alpha通道編碼

### 色彩轉換演算法

#### SRF到PNG（解碼）
SRF使用16位色彩格式（RGB565），解碼公式：
- 紅色：`((值 & 0xF800) >> 11) << 3`
- 綠色：`((值 & 0x07E0) >> 5) << 2`
- 藍色：`(值 & 0x001F) << 3`

#### PNG到SRF（編碼）
24位色彩轉換為16位RGB565格式：
- 紅色：`(red >> 3) << 11`
- 綠色：`(green >> 2) << 5`
- 藍色：`blue >> 3`

## 故障排除

### 常見錯誤

#### SRF到PNG轉換

1. **"無效的SRF檔案"**：
   - 檢查檔案是否為有效的SRF格式
   - 確認檔案未損壞

2. **"檔案已存在"**：
   - 使用`-f`選項強制覆蓋
   - 或先刪除現有檔案

#### PNG到SRF轉換

1. **"找不到檔案"**：
   - 確保PNG檔案和資訊檔案都存在
   - 檢查檔案名稱是否正確

2. **"PNG檔案太小"**：
   - 確保PNG圖像尺寸與資訊檔案中記錄的尺寸一致

3. **"資訊檔案不包含有效資料"**：
   - 檢查資訊檔案格式是否正確
   - 確保所有必要的欄位都存在

### 通用錯誤

1. **Python模組錯誤**：
   - 確認已安裝Pillow：`pip3 list | grep Pillow`
   - 重新安裝：`pip3 install --upgrade Pillow`

### 除錯技巧

在程式中加入更多除錯訊息：
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 品質保證

### 轉換品質驗證
- 雙向轉換應該保持圖像品質
- 建議使用相同的分離遮罩設定進行往返轉換
- alpha通道資料在轉換過程中完全保留

### 檔案完整性
- 程式會驗證輸入檔案的完整性
- 自動檢查圖像尺寸和段數一致性
- 提供詳細的錯誤訊息以協助問題診斷

## 限制事項

1. **圖像段數量**：最多支援9個圖像段
2. **圖像格式**：PNG必須為RGB或RGBA格式
3. **檔案大小**：受系統記憶體限制
4. **色彩精度**：16位色彩轉換可能有輕微的精度損失

## 授權和貢獻

這個程式是從原始Java版本移植而來，目的是提供跨平台的SRF轉換功能。

## 更新歷史

- v1.0: 初始Python版本，SRF到PNG轉換
- v1.1: 加入PNG到SRF轉換功能，完整雙向支援