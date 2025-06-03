#!/usr/bin/env python3
"""
PNG到SRF轉換器 - Python版本
將PNG格式圖像文件轉換為Garmin SRF格式

使用方法: python png2srf.py [選項] <png基礎名> <srf檔案名>
選項:
  -f 強制覆蓋現有檔案
"""

import sys
import os
import struct
import argparse
from PIL import Image
import io


class Png2Srf:
    """PNG到SRF轉換器類別"""

    def __init__(self):
        """初始化轉換器"""
        self.checksum = 0
        self.section_count = 0
        self.section_widths = [0] * 10  # 最多支援10個圖像段
        self.section_heights = [0] * 10
        self.rgb_image = None
        self.mask_image = None

    def convert(self, png_base, srf_filename, force_overwrite=False):
        """
        轉換PNG檔案為SRF格式

        參數:
        png_base: PNG檔案的基礎名稱
        srf_filename: SRF輸出檔案路徑
        force_overwrite: 是否強制覆蓋現有檔案
        """

        # 處理檔案名稱的便利功能
        if png_base.lower().endswith('.png'):
            print("注意: 移除png_base末尾的'.png'")
            png_base = png_base[:-4]

        # 檢查必要的輸入檔案
        required_files = [
            f"{png_base}.png",
            f"{png_base}_info.txt"
        ]

        for filename in required_files:
            if not os.path.exists(filename):
                print(f"錯誤: 找不到檔案 '{filename}'")
                return False

        # 自動添加.srf副檔名
        if not self._get_extension(srf_filename):
            print("注意: 在srf_filename末尾添加'.srf'")
            srf_filename += '.srf'

        # 檢查輸出檔案是否已存在
        if not force_overwrite and os.path.exists(srf_filename):
            print(f"錯誤: 檔案 '{srf_filename}' 已存在。使用 '-f' 選項來覆蓋現有檔案")
            return False

        try:
            # 讀取資訊檔案
            info_data = self._read_info_file(f"{png_base}_info.txt")
            if not info_data:
                return False

            mask_filename, full_image_width, full_image_height = info_data

            # 驗證圖像段資訊
            if not self._validate_sections():
                return False

            # 載入圖像檔案
            if not self._load_images(f"{png_base}.png", mask_filename, full_image_width, full_image_height):
                return False

            # 寫入SRF檔案
            return self._write_srf_file(srf_filename)

        except Exception as e:
            print(f"處理檔案時發生錯誤: {e}")
            return False

    def _read_info_file(self, info_filename):
        """讀取資訊檔案"""
        mask_filename = None
        full_image_width = 0
        full_image_height = 0

        try:
            with open(info_filename, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if ':' in line:
                        label, value = line.split(':', 1)
                        label = label.strip()
                        value = value.strip()

                        if label == "MaskFile":
                            if value != "<none>":
                                mask_filename = value
                        elif label == "Width":
                            full_image_width = self._safe_parse_int(value)
                        elif label == "Height":
                            full_image_height = self._safe_parse_int(value)
                        elif label == "SectionCount":
                            self.section_count = self._safe_parse_int(value)
                        elif label.startswith("SectionWidth") and len(label) == 13:
                            section_num = self._safe_parse_int(label[12])
                            if section_num > 0:
                                self.section_widths[section_num - 1] = self._safe_parse_int(value)
                        elif label.startswith("SectionHeight") and len(label) == 14:
                            section_num = self._safe_parse_int(label[13])
                            if section_num > 0:
                                self.section_heights[section_num - 1] = self._safe_parse_int(value)

            return mask_filename, full_image_width, full_image_height

        except Exception as e:
            print(f"讀取資訊檔案時發生錯誤: {e}")
            return None

    def _validate_sections(self):
        """驗證圖像段資訊"""
        if self.section_count == 0:
            print("錯誤: 資訊檔案不包含有效的段數")
            return False

        for i in range(self.section_count):
            if self.section_heights[i] == 0 or self.section_widths[i] == 0:
                print(f"錯誤: 資訊檔案不包含段 {i+1} 的有效尺寸")
                return False
            else:
                print(f"圖像段尺寸: {self.section_widths[i]}x{self.section_heights[i]}")

        return True

    def _load_images(self, png_filename, mask_filename, expected_width, expected_height):
        """載入PNG圖像檔案"""
        try:
            # 計算期望的圖像尺寸
            expected_image_width = max(self.section_widths[:self.section_count])
            expected_image_height = sum(self.section_heights[:self.section_count])

            if expected_image_width != expected_width or expected_image_height != expected_height:
                print("警告: 圖像檔案中的圖像尺寸不匹配")

            # 載入主要圖像
            self.rgb_image = Image.open(png_filename)

            # 載入遮罩圖像（如果存在）
            if mask_filename:
                print("轉換PNG為SRF，使用分離的alpha遮罩")
                self.mask_image = Image.open(mask_filename)

                if (self.mask_image.width < expected_image_width or
                    self.mask_image.height < expected_image_height):
                    print("遮罩檔案太小，無法包含所有圖像段")
                    return False
            else:
                print("轉換PNG為SRF")

            # 檢查圖像尺寸
            if (self.rgb_image.width < expected_image_width or
                self.rgb_image.height < expected_image_height):
                print("PNG檔案太小，無法包含所有圖像段")
                return False

            return True

        except Exception as e:
            print(f"載入圖像檔案時發生錯誤: {e}")
            return False

    def _write_srf_file(self, srf_filename):
        """寫入SRF檔案"""
        try:
            with open(srf_filename, 'wb') as srf_file:
                # 寫入SRF標頭
                self._write_srf_header(srf_file)

                # 寫入每個圖像段
                cur_y_pos = 0
                for i in range(self.section_count):
                    self._write_image_section(srf_file, i, cur_y_pos)
                    cur_y_pos += self.section_heights[i]

                # 寫入SRF結尾
                self._write_srf_footer(srf_file)

            print("轉換完成！")
            return True

        except Exception as e:
            print(f"寫入SRF檔案時發生錯誤: {e}")
            return False

    def _write_srf_header(self, srf_file):
        """寫入SRF檔案標頭"""
        # 檔案識別字串
        file_id = b"GARMIN BITMAP 01"
        srf_file.write(file_id)
        self._add_bytes_to_checksum(file_id)

        # 寫入標頭資料
        self._write_int32(srf_file, 4)
        self._write_int32(srf_file, 4)
        self._write_int32(srf_file, self.section_count)
        self._write_int32(srf_file, 5)
        self._write_p_string(srf_file, "578")
        self._write_int32(srf_file, 6)
        self._write_p_string(srf_file, "1.00")
        self._write_int32(srf_file, 7)
        self._write_p_string(srf_file, "006-D0578-XX")

    def _write_image_section(self, srf_file, section_num, y_base):
        """寫入單個圖像段"""
        w = self.section_widths[section_num]
        h = self.section_heights[section_num]

        # 圖像段標頭
        self._write_int32(srf_file, 0)
        self._write_int32(srf_file, 16)
        self._write_int32(srf_file, 0)
        self._write_int16(srf_file, h)
        self._write_int16(srf_file, w)
        self._write_int16(srf_file, 2064)
        self._write_int16(srf_file, w * 2)
        self._write_int32(srf_file, 0)

        # Alpha資料
        self._write_int32(srf_file, 11)
        self._write_int32(srf_file, w * h)

        for y in range(h):
            for x in range(w):
                if self.mask_image:
                    # 從遮罩圖像獲取alpha值
                    pixel = self.mask_image.getpixel((x, y + y_base))
                    if isinstance(pixel, tuple):
                        alpha = pixel[0]  # 取第一個通道
                    else:
                        alpha = pixel
                else:
                    # 從RGB圖像的alpha通道獲取
                    pixel = self.rgb_image.getpixel((x, y + y_base))
                    if len(pixel) >= 4:
                        alpha = pixel[3]  # RGBA的A通道
                    else:
                        alpha = 255  # 預設為完全不透明

                encoded_alpha = self._encode_alpha(alpha)
                srf_file.write(bytes([encoded_alpha]))
                self.checksum += encoded_alpha

        # RGB資料
        self._write_int32(srf_file, 1)
        self._write_int32(srf_file, w * h * 2)

        for y in range(h):
            for x in range(w):
                pixel = self.rgb_image.getpixel((x, y + y_base))
                if len(pixel) >= 3:
                    color = (pixel[0] << 16) | (pixel[1] << 8) | pixel[2]  # RGB
                else:
                    color = 0

                encoded_color = self._encode_color(color)
                self._write_int16(srf_file, encoded_color)

    def _write_srf_footer(self, srf_file):
        """寫入SRF檔案結尾"""
        # 計算填充位元組
        bytes_written = srf_file.tell()
        bytes_to_write = 255 - (bytes_written % 256)

        for _ in range(bytes_to_write):
            srf_file.write(b'\xff')
            self.checksum += 0xff

        # 寫入檢查位元組
        checkbyte = (256 - (self.checksum & 255)) & 255
        srf_file.write(bytes([checkbyte]))

    def _encode_color(self, color):
        """將24位顏色編碼為16位"""
        r = (color & 0xff0000) >> 19  # 取高5位
        g = (color & 0x00ff00) >> 11  # 取高6位
        b = (color & 0x0000ff) >> 3   # 取高5位
        return (r << 11) | (g << 5) | b

    def _encode_alpha(self, alpha):
        """將8位alpha值編碼為7位反轉值"""
        a = (255 - (alpha & 255)) >> 1
        if a == 127:
            return 128
        return a

    def _write_p_string(self, srf_file, string):
        """寫入前綴長度的字串"""
        self._write_int32(srf_file, len(string))
        string_bytes = string.encode('ascii')
        srf_file.write(string_bytes)
        self._add_bytes_to_checksum(string_bytes)

    def _write_int32(self, srf_file, value):
        """寫入小端序32位整數"""
        for i in range(4):
            byte_val = value & 255
            srf_file.write(bytes([byte_val]))
            self.checksum += byte_val
            value >>= 8

    def _write_int16(self, srf_file, value):
        """寫入小端序16位整數"""
        for i in range(2):
            byte_val = value & 255
            srf_file.write(bytes([byte_val]))
            self.checksum += byte_val
            value >>= 8

    def _add_bytes_to_checksum(self, byte_data):
        """將位元組資料加入檢查和"""
        for byte in byte_data:
            self.checksum += byte

    def _safe_parse_int(self, s):
        """安全地解析整數"""
        try:
            return int(s)
        except ValueError:
            return 0

    def _get_extension(self, filename):
        """取得檔案副檔名"""
        _, ext = os.path.splitext(filename)
        return ext


def print_usage():
    """顯示使用說明"""
    print()
    print("使用方法: python png2srf.py [選項] <png基礎名> <srf檔案名>")
    print()
    print("選項:")
    print("  -f  強制覆蓋現有檔案")
    print()
    print("範例: python png2srf.py vehicle newvehicle.srf")
    print("  讀取 vehicle_info.txt、vehicle.png（以及")
    print("  可能的 vehicle_mask.png），並輸出")
    print("  newvehicle.srf")
    print()


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='PNG到SRF轉換器', add_help=False)
    parser.add_argument('-f', action='store_true', help='強制覆蓋現有檔案')
    parser.add_argument('-h', '--help', action='store_true', help='顯示幫助訊息')
    parser.add_argument('files', nargs='*', help='輸入和輸出檔案')

    try:
        args = parser.parse_args()

        if args.help or len(args.files) != 2:
            print_usage()
            return

        png_base, srf_filename = args.files

        converter = Png2Srf()
        success = converter.convert(png_base, srf_filename, args.f)

        if not success:
            print("轉換失敗！")
            sys.exit(1)

    except Exception as e:
        print(f"發生錯誤: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()