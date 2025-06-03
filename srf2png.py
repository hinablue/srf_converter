#!/usr/bin/env python3
"""
SRF到PNG轉換器 - Python版本
將Garmin SRF格式圖像文件轉換為PNG格式

使用方法: python srf2png.py [選項] <srf檔案名> <png基礎名>
選項:
  -m 使用分離的alpha遮罩圖像
  -f 強制覆蓋現有檔案
"""

import sys
import os
import struct
import argparse
from PIL import Image
import io


class Srf2Png:
    """SRF到PNG轉換器類別"""

    def __init__(self):
        """初始化轉換器"""
        self.checksum = 0
        self.section_count = 0
        self.section_widths = [0] * 10  # 最多支援10個圖像段
        self.section_heights = [0] * 10
        self.rgb_image = None
        self.mask_image = None

    def convert(self, srf_filename, png_base, separate_mask=False, force_overwrite=False):
        """
        轉換SRF檔案為PNG格式

        參數:
        srf_filename: SRF檔案路徑
        png_base: PNG輸出檔案的基礎名稱
        separate_mask: 是否使用分離的alpha遮罩
        force_overwrite: 是否強制覆蓋現有檔案
        """

        # 處理檔案名稱的便利功能
        if png_base.lower().endswith('.png'):
            print("注意: 移除png_base末尾的'.png'")
            png_base = png_base[:-4]

        # 自動添加.srf副檔名
        if not self._get_extension(srf_filename) and not os.path.exists(srf_filename):
            if os.path.exists(srf_filename + '.srf'):
                print("注意: 在srf_filename末尾添加'.srf'")
                srf_filename += '.srf'

        if not os.path.exists(srf_filename):
            print(f"錯誤: 找不到SRF檔案 '{srf_filename}'")
            return False

        # 輸出檔案名稱列表
        output_files = [
            f"{png_base}.png",
            f"{png_base}_mask.png",
            f"{png_base}_info.txt"
        ]

        if separate_mask:
            print("轉換SRF為PNG，使用分離的alpha遮罩")
        else:
            print("轉換SRF為PNG")

        # 檢查檔案是否已存在
        if not force_overwrite:
            for filename in output_files:
                if os.path.exists(filename):
                    print(f"錯誤: 檔案 '{filename}' 已存在。使用 '-f' 選項來覆蓋現有檔案")
                    return False

        try:
            # 開始處理SRF檔案
            with open(srf_filename, 'rb') as srf_file:
                return self._process_srf_file(srf_file, output_files, separate_mask)

        except Exception as e:
            print(f"處理檔案時發生錯誤: {e}")
            return False

    def _process_srf_file(self, srf_file, output_files, separate_mask):
        """處理SRF檔案的主要邏輯"""

        # 讀取檔案標頭
        file_identifier = self._read_basic_string(srf_file, 16)
        if file_identifier != "GARMIN BITMAP 01":
            print("無效的SRF檔案")
            return False

        # 跳過未知用途的位元組
        srf_file.seek(8, 1)  # 4,4 -- 用途未知
        self.section_count = self._read_int32(srf_file)
        srf_file.seek(4, 1)  # 5 -- 用途未知
        srf_file.seek(7, 1)  # P"578"
        srf_file.seek(4, 1)  # 6 -- 用途未知

        version_string = self._read_p_string(srf_file)
        srf_file.seek(4, 1)  # 7 -- 用途未知
        product_string = self._read_p_string(srf_file)

        print(f"SRF版本:     {version_string}")
        print(f"SRF產品:     {product_string}")
        print(f"圖像段數:    {self.section_count}")

        # 檢查圖像段數量限制
        if self.section_count > 9:
            print("錯誤: 此SRF檔案的圖像段過多")
            return False

        # 讀取所有段的尺寸資訊
        self._read_section_sizes(srf_file)

        # 計算完整圖像尺寸
        full_image_width = max(self.section_widths[:self.section_count]) if self.section_count > 0 else 0
        full_image_height = sum(self.section_heights[:self.section_count])

        # 創建圖像物件
        if separate_mask:
            self.rgb_image = Image.new('RGB', (full_image_width, full_image_height))
            self.mask_image = Image.new('L', (full_image_width, full_image_height))
        else:
            self.rgb_image = Image.new('RGBA', (full_image_width, full_image_height))

        # 讀取每個圖像段
        cur_y_pos = 0
        for i in range(self.section_count):
            self._read_image_section(srf_file, cur_y_pos, separate_mask)
            cur_y_pos += self.section_heights[i]

        # 儲存PNG檔案
        self.rgb_image.save(output_files[0], 'PNG')
        if separate_mask:
            self.mask_image.save(output_files[1], 'PNG')

        # 寫入資訊檔案
        self._write_info_file(output_files[2], output_files[1] if separate_mask else "<none>",
                             full_image_width, full_image_height)

        return True

    def _read_section_sizes(self, srf_file):
        """讀取所有圖像段的尺寸資訊"""
        # 記住當前位置
        initial_position = srf_file.tell()

        for i in range(self.section_count):
            srf_file.seek(12, 1)  # 跳過未知資料
            h = self._read_int16(srf_file)
            w = self._read_int16(srf_file)
            self.section_heights[i] = h
            self.section_widths[i] = w
            # 跳過這個段的其餘資料
            srf_file.seek(8 + 8 + w*h + 8 + w*h*2, 1)

        # 回到原始位置
        srf_file.seek(initial_position)

    def _read_image_section(self, srf_file, y_base, separate_mask):
        """讀取單個圖像段"""
        # 讀取圖像標頭
        srf_file.seek(12, 1)  # 0,16,0 -- 用途未知
        height = self._read_int16(srf_file)
        width = self._read_int16(srf_file)
        srf_file.seek(2, 1)   # 16,8 -- 用途未知
        linebytes = self._read_int16(srf_file)
        srf_file.seek(4, 1)   # 0 -- 用途未知

        print(f"圖像段尺寸: {width}x{height}")

        # 讀取alpha資料
        srf_file.seek(4, 1)  # 11 -- 可能是資料類型
        srf_file.seek(4, 1)  # 資料長度，等於width*height
        alpha_buffer = srf_file.read(width * height)

        # 讀取RGB資料
        srf_file.seek(4, 1)  # 1 -- 可能是資料類型
        srf_file.seek(4, 1)  # 資料長度，等於width*height*2
        rgb_buffer = srf_file.read(width * height * 2)

        # 將資料寫入記憶體中的圖像
        for y in range(height):
            for x in range(width):
                pos = y * width + x
                alpha = self._decode_alpha(alpha_buffer[pos])
                color = self._decode_color(rgb_buffer[pos*2], rgb_buffer[pos*2+1])

                if separate_mask:
                    self.rgb_image.putpixel((x, y_base + y), color)
                    self.mask_image.putpixel((x, y_base + y), alpha)
                else:
                    rgba_color = color + (alpha,)
                    self.rgb_image.putpixel((x, y_base + y), rgba_color)

    def _decode_color(self, b1, b2):
        """將16位顏色轉換為24位顏色"""
        v = (b2 << 8) + b1
        r = ((v & 0xf800) >> 11) << 3  # 5位紅色轉8位
        g = ((v & 0x07e0) >> 5) << 2   # 6位綠色轉8位
        b = (v & 0x001f) << 3          # 5位藍色轉8位
        return (r, g, b)

    def _decode_alpha(self, b):
        """將7位反轉alpha值轉換為8位標準值"""
        a = (b & 0xff) << 1
        if a >= 254:
            a = 255
        return 255 - a

    def _read_p_string(self, srf_file):
        """讀取前綴長度的字串"""
        length = self._read_int32(srf_file)
        return self._read_basic_string(srf_file, length)

    def _read_basic_string(self, srf_file, length):
        """讀取指定長度的字串"""
        data = srf_file.read(length)
        return data.decode('ascii', errors='ignore')

    def _read_int16(self, srf_file):
        """讀取小端序16位整數"""
        data = srf_file.read(2)
        return struct.unpack('<H', data)[0]

    def _read_int32(self, srf_file):
        """讀取小端序32位整數"""
        data = srf_file.read(4)
        return struct.unpack('<I', data)[0]

    def _write_info_file(self, filename, mask_file, width, height):
        """寫入資訊檔案"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"MaskFile: {mask_file}\n")
            f.write(f"Width: {width}\n")
            f.write(f"Height: {height}\n")
            f.write(f"SectionCount: {self.section_count}\n")
            for i in range(self.section_count):
                f.write(f"SectionWidth{i+1}: {self.section_widths[i]}\n")
                f.write(f"SectionHeight{i+1}: {self.section_heights[i]}\n")

    def _get_extension(self, filename):
        """取得檔案副檔名"""
        _, ext = os.path.splitext(filename)
        return ext


def print_usage():
    """顯示使用說明"""
    print()
    print("使用方法: python srf2png.py [選項] <srf檔案名> <png基礎名>")
    print()
    print("選項:")
    print("  -m  使用分離的alpha遮罩圖像")
    print("  -f  強制覆蓋現有檔案")
    print()
    print("範例: python srf2png.py -m vehicle.srf newvehicle")
    print("  讀取 vehicle.srf 並創建 newvehicle.png、")
    print("  newvehicle_mask.png 和 newvehicle_info.txt")
    print()


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='SRF到PNG轉換器', add_help=False)
    parser.add_argument('-m', action='store_true', help='使用分離的alpha遮罩')
    parser.add_argument('-f', action='store_true', help='強制覆蓋現有檔案')
    parser.add_argument('-h', '--help', action='store_true', help='顯示幫助訊息')
    parser.add_argument('files', nargs='*', help='輸入和輸出檔案')

    try:
        args = parser.parse_args()

        if args.help or len(args.files) != 2:
            print_usage()
            return

        srf_filename, png_base = args.files

        converter = Srf2Png()
        success = converter.convert(srf_filename, png_base, args.m, args.f)

        if success:
            print("轉換完成！")
        else:
            print("轉換失敗！")
            sys.exit(1)

    except Exception as e:
        print(f"發生錯誤: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()