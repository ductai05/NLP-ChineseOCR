# Fine-tune PaddleOCR for NomNaOCR
## Online dataset, resource
- [NomNaOCR](https://www.kaggle.com/datasets/quandang/nomnaocr): Dataset for the old Vietnamese Hán-Nôm scrip.
- [CWKB](https://kabc.dongguk.edu/content/list?itemId=ABC_BJ): Complete Works of Korean Buddhism.
- [Dataset-NLP_Final](https://www.kaggle.com/datasets/dinhducanhkhoa/dataset-nlp-final): The cleaned, combined, and pre-processed NomNaOCR and CWKB dataset.
- [Model-NLP_Final](https://www.kaggle.com/datasets/nguyenlehoangtrung/model-nlp-final): Fine-tuned PaddleOCR model (model checkpoints and configuration) for NomNaOCR text detection.
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR): PaddleOCR repository.
- [PaddleOCR-Tutorial](https://www.paddleocr.ai/latest/en/version3.x/module_usage/text_detection.html): PaddleOCR tutorial for text detection.

## Project Resources
- `1_fine-tuning.ipynb`: Environment setup, pre-trained model download, and PP-OCRv5 fine-tuning.
- `2_evaluation.ipynb`: Model evaluation, inference export, and training visualization.
- `train_log.png`: Training loss and metrics visualization.
- `PP-OCRv5_server_det/`: Training configuration and logs (Best model weights in [Model-NLP_Final](https://www.kaggle.com/datasets/nguyenlehoangtrung/model-nlp-final)/PP-OCRv5_server_det/best_model/model.pdparams).
- `inference_results/`: Detection results visualized on test images.
- `error_analysis/`: Best and worst performing samples for error analysis.