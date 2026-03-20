# Chinese OCR: Fine-tune PaddleOCR cho bài toán phát hiện chữ Hán Nôm

Đồ án môn học: **Nhập môn xử lý ngôn ngữ tự nhiên - CQ2023/22**, Khoa Công nghệ thông tin, Trường Đại học Khoa học tự nhiên, ĐHQG-HCM.

## Thành viên nhóm thực hiện

- Đinh Đức Anh Khoa (23122001)
- Nguyễn Lê Hoàng Trung (23122004)
- Đinh Đức Tài (23122013)

**Giáo viên hướng dẫn:**
- PGS.TS. Đinh Điền
- TS. Nguyễn Hồng Bửu Long
- TS. Lương An Vinh
- CN. Trần Kim Phát

---

## 1. Giới thiệu

Dự án này tập trung vào việc fine-tune mô hình **PP-OCRv5_server_det** của **PaddleOCR** cho bài toán phát hiện chữ Hán Nôm (Text Detection) trên hai bộ dữ liệu lớn là **NomNaOCR** và **CWKB** (Toàn tập Phật giáo Hàn Quốc - Complete Works of Korean Buddhism). 

Kết quả sau quá trình tinh chỉnh (full fine-tuning) cho thấy hiệu năng mô hình được cải thiện rõ rệt, đặc biệt trên các tập dữ liệu nhiễu và phức tạp.

## 2. Dữ liệu sử dụng

Dự án sử dụng hai nguồn dữ liệu chính được chuẩn hóa và gán nhãn:
- **NomNaOCR:** Bộ dữ liệu OCR lớn nhất hiện nay cho chữ Hán-Nôm ở Việt Nam (được xây dựng từ Lục Vân Tiên, Truyện Kiều, Đại Việt Sử Ký Toàn Thư).
- **CWKB:** Toàn tập Phật giáo Hàn Quốc, nguồn tư liệu gốc quan trọng, được nhóm thu thập tự động (crawl), làm sạch và gán nhãn thủ công bổ sung.

Dữ liệu được chia theo tỷ lệ Train/Val/Test với số lượng ảnh lần lượt là 2253, 564 và 594 ảnh.

## 3. Cấu trúc thư mục (Codebase)

- **`CWKB/`**: Chứa các scripts liên quan đến việc thu thập và tiền xử lý dữ liệu CWKB.
  - `crawl/`: Thu thập dữ liệu hình ảnh.
  - `bbox adjust/`: Điều chỉnh Bounding Box cho dữ liệu.
  - `data preparation/`: Chuẩn bị dữ liệu huấn luyện.
- **`Finetune/`**: Mã nguồn dùng để huấn luyện và đánh giá mô hình.
  - `data_preparation/`: Cấu trúc gộp và định dạng lại cấu trúc thư mục của CWKB & NomNaOCR.
  - `1_fine-tuning.ipynb`: Thiết lập môi trường, tải pre-trained model và thực hiện tinh chỉnh PP-OCRv5.
  - `2_evaluation.ipynb`: Đánh giá mô hình, trực quan hóa trong quá trình huấn luyện và trích xuất kết quả dự đoán.
  - `PP-OCRv5_server_det/`: Chứa config huấn luyện và log.
  - `error_analysis/`: Phân tích lỗi các mẫu phát hiện tốt nhất và dự đoán tệ nhất.
  - `train_log.png`: Biểu đồ trực quan metric và quá trình huấn luyện.

## 4. Chi tiết huấn luyện mô hình (PP-OCRv5)

- **Kiến trúc mô hình:** PP-OCRv5 Server Detection thuật toán DB.
- **Backbone:** PP-HGNetV2_B4.
- **Neck:** LKPAN (Large Kernel Path Aggregation Network).
- **Phương pháp:** Full Fine-tuning trên nền tảng Kaggle (Sử dụng 2 GPU NVIDIA Tesla T4).
- **Epochs:** 100.
- **Optimizer:** Adam ($\beta_1$ = 0.9, $\beta_2$ = 0.999), với tốc độ học khởi tạo 0.001 (chiến lược Cosine Annealing).
- **Hàm Loss:** DBLoss (tổ hợp có trọng số của Probability map loss với DiceLoss và Threshold map loss với Binary Cross Entropy).
- **Data Augmentation:** Random crop kích thước mặc định 640x640, xoay ảnh ngẫu nhiên, lật ngang ảnh ngẫu nhiên.

## 5. Kết quả (Phân tích trên tập Test NomNaOCR)

Mô hình sau khi tinh chỉnh đạt được sức mạnh vượt trội về chỉ số H-mean so với mô hình gốc ban đầu:

| Metric | Mô hình gốc (`PP-OCRv5_server_det`) | Mô hình đã tinh chỉnh (Fine-tuned) |
| --- | --- | --- |
| **Precision** | 0.713 | 0.966 |
| **Recall** | 0.750 | 0.937 |
| **H-mean** | **0.731** | **0.952** |

Mô hình hội tụ rất nhanh, đạt tiệm cận mức lý tưởng sau 20 epoch. Các tác phẩm in ấn rõ chữ đạt biên lợi nhuận H-mean cực kì cao, thay vào đó mô hình bị hạn chế (do thiếu module tiền xử lý giảm nhiễu tiền kì) ở những tác phẩm ảnh mờ nhòe như bộ Đại Việt sử ký toàn thư.

## 6. Công nghệ / Tài nguyên trực tuyến

- **Ngôn ngữ & Framework:** Python, PaddlePaddle GPU, PaddleOCR.
- **Bộ dữ liệu gốc:** [NomNaOCR](https://www.kaggle.com/datasets/quandang/nomnaocr), [CWKB](https://kabc.dongguk.edu/content/list?itemId=ABC_BJ).
- **Bộ dữ liệu đã chuẩn hóa:** [Dataset-NLP_Final](https://www.kaggle.com/datasets/dinhducanhkhoa/dataset-nlp-final).
- **Model checkpoints & Cấu hình:** [Model-NLP_Final](https://www.kaggle.com/datasets/nguyenlehoangtrung/model-nlp-final).
- **Dữ liệu Inference:** [Results-NLP_Final](https://www.kaggle.com/datasets/nguyenlehoangtrung/results-nlp-final).
