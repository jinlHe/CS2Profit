from rapidocr_onnxruntime import RapidOCR
import cv2
import numpy as np
from pathlib import Path
import onnxruntime as ort

class LongImageOCR:
    def __init__(self):
        """
        初始化OCR识别器，优先使用GPU
        """
        # 检查可用的设备
        providers = []
        if 'CUDAExecutionProvider' in ort.get_available_providers():
            providers.append('CUDAExecutionProvider')
            print("使用 CUDA GPU 进行处理")
        else:
            print("未检测到可用的GPU，将使用CPU处理")
        providers.append('CPUExecutionProvider')
        
        # 初始化RapidOCR，设置为使用GPU
        self.ocr = RapidOCR(providers=providers)
        print("OCR引擎初始化完成")
        
    def segment_image(self, image, segment_height=1000, overlap=50):
        """
        将长图片分割成多个小段
        
        Args:
            image: 输入的图片数组
            segment_height: 每个分段的高度
            overlap: 分段之间的重叠像素，防止文字被切断
            
        Returns:
            list: 分割后的图片段列表
        """
        height, width = image.shape[:2]
        segments = []
        
        for start_y in range(0, height, segment_height - overlap):
            end_y = min(start_y + segment_height, height)
            segment = image[start_y:end_y]
            segments.append((segment, start_y))
            
            if end_y == height:
                break
                
        return segments
    
    def process_image(self, image_path, segment_height=1000, overlap=50):
        """
        处理长图片并识别文字
        
        Args:
            image_path: 图片路径
            segment_height: 分段高度
            overlap: 重叠区域大小
            
        Returns:
            list: 识别出的文字列表，每个元素包含文字内容和其在原图中的位置信息
        """
        # 读取图片
        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError(f"无法读取图片: {image_path}")
            
        # 分割图片
        segments = self.segment_image(image, segment_height, overlap)
        all_results = []
        
        # 处理每个分段
        total_segments = len(segments)
        for idx, (segment, start_y) in enumerate(segments, 1):
            print(f"正在处理第 {idx}/{total_segments} 段...")
            # 识别文字
            result, elapse = self.ocr(segment)
            
            if result:
                # 调整y坐标以匹配原图位置
                for box, text, confidence in result:
                    # RapidOCR的box格式为[[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                    adjusted_box = [[int(p[0]), int(p[1] + start_y)] for p in box]
                    all_results.append({
                        'text': text,
                        'confidence': confidence,
                        'position': adjusted_box,
                        'y_coord': start_y + int(box[0][1])  # 用于排序
                    })
        
        # 按照y坐标和x坐标排序，确保文字从上到下、从左到右的顺序
        all_results.sort(key=lambda x: (x['y_coord'], x['position'][0][0]))
        
        return all_results

    def save_results(self, results, output_path):
        """
        将识别结果保存到文件
        
        Args:
            results: 识别结果列表
            output_path: 输出文件路径
        """
        # 确保输出目录存在
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存文本结果
        with open(output_path, 'w', encoding='utf-8') as f:
            for result in results:
                confidence_str = f"{result['confidence']:.2f}"
                f.write(f"{result['text']} (置信度: {confidence_str})\n")

def main():
    # 创建OCR处理器实例
    ocr = LongImageOCR()
    
    # 设置输入输出路径
    image_path = '../youyou/sell2.JPG'
    output_path = '../youyou/ocr_sell2_results.txt'
    
    try:
        # 处理图片
        print("开始处理图片...")
        results = ocr.process_image(image_path)
        
        # 保存结果
        ocr.save_results(results, output_path)
        print(f"识别完成！结果已保存到: {output_path}")
        
        # 打印识别到的文字数量
        print(f"共识别出 {len(results)} 处文字")
        
    except Exception as e:
        print(f"处理过程中出现错误: {str(e)}")

if __name__ == '__main__':
    main() 