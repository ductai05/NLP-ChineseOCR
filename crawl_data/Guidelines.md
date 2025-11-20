# Group Information

| Scripture Numbers | Total Books | Group Members | Group leader |
| :---: | :---: | :---: | :---: |
| H0001 \- H0004 | 4 | 1 | Nguyễn Phạm Văn Khải |
| H0005 \- H0020 | 16 | 4 | Nguyễn Hải Đăng |
| H0021 \- H0028 | 8 | 2 | Thanh Tùng |
| H0029 \- H0040 | 12 | 3 | Anh Khoa |
| H0041 \- H0044 | 4 | 1 | Tuấn Anh |
| H0045 \- H0048 | 4 | 1 | Phạm Mạnh Trung |
| H0193 \- H0225 | 33 |  |  |
| H0226 \- H0258 | 33 |  |  |
| H0259 \- H0291 | 33 |  |  |
| H0292 \- H0324 | 33 |  |  |

# Guidelines

We need to crawl data from [kabc.dongguk.edu](https://kabc.dongguk.edu/content/view?dataId=ABC_BJ_H0246_T_001&rt=T)

# Overview of the website

![][image1]  
**Scriptures Panel (Left Sidebar)**

- Each book is labeled with a scripture number (e.g., H0264).  
- Clicking expands chapters below it.

**Chapters**

- Selecting a chapter triggers the website to render the full punctuated transcription.  
- Important: Chapters may show sub-chapters. Ignore these sub-chapters.

**Text Content (Main Display Panel)**

- This is the transcription of the scanned images. This includes the ancient transcription (pink background) and translated text (white background).  
- The text is displayed page by page for all pages within the selected chapter.

**Image Content**

- Each page will have a button to open a new site to view the image.  
- By accessing the attribute ‘data-xsl-kid’ of this button, we will retrieve the **image id**.  
- Send the GET request to the following URL to download the image:  [https://kabc.dongguk.edu/data/image/ABC\_BJ/ABC\_BJ\_{scripture\_number}/ABC\_BJ\_{scripture\_number}\_{image\_id}.jpg](https://kabc.dongguk.edu/data/image/ABC_BJ/ABC_BJ_{scripture_number}/ABC_BJ_{scripture_number}{image_id}.jpg)  
- For example:  scripture number \= H0246 and image id \= 010\_0758\_b  
  [https://kabc.dongguk.edu/data/image/ABC\_BJ/ABC\_BJ\_H0246/ABC\_BJ\_H0246\_010\_0758\_b.jpg](https://kabc.dongguk.edu/data/image/ABC_BJ/ABC_BJ_H0246/ABC_BJ_H0246_010_0758_b.jpg)

# Requirements

- Crawl **all the images along with their ancient transcriptions** of each assigned book.  
- Pre-process the content for OCR dataset:  
  - For image: resize each one so that its largest dimension is 2048 pixels, scaling the other dimension proportionally to preserve the original aspect ratio.  
  - For text: remove punctuation and whitespaces from the text for recognition dataset.  
- Annotate images semi-automatically to obtain **at least 3000 bounding boxes per member**:  
  - Use CLCLab or PaddleOCR’s text detection models to generate pseudo-bounding boxes  
  - Manually correct these boxes with annotation tools such as [PPOCRLabel](https://github.com/PFCCLab/PPOCRLabel.git)  
- Annotate transcription for each annotated bounding box:  
  - Align the text (without punctuation) to the corresponding text box.  
- Output:  
  ![][image2]  
    
  The format of **rec\_gt.txt** and **det\_gt.txt** label files are defined as follow to train with PaddleOCR:  
  ![][image3]


	**results.xlsx** contains all of your **annotated** text lines:

| Image ID | Patch ID | Bounding Box | Sino-Nom OCR |
| :---- | :---- | :---- | :---- |
| H0246\_010\_0758\_b.jpg | H0246\_010\_0758\_b.001 | \[\[100, 200\], \[300, 400\], \[500, 600\], \[700, 800\]\] | t山即東海上巨靈也 |
| H0246\_010\_0758\_b.jpg | H0246\_010\_0758\_b.002 | Bounding box of the second text line | Content of the second text line |
| … | … | … | … |

	

# Notes

1. These scriptures are read from **right to left** and from **top to bottom**.  
2. All patches must be numbered according to their reading order on the page.  
3. All cropped text line images must be rotated 90 degrees **counter-clockwise** before being saved to patches directory.  
4. Before crawling, the crawler **must check and respect** the website’s **robots.txt** rules. Avoid sending too many requests within a short time to prevent overloading the server.

# 

# Examples

| Image | Text with Punctuation |
| :---- | :---- |
| ![][image4] | 月荷上人遺集序 余未見師。不知師爲何許人。讀其詩 觀其志。始得其八九分。殆是心儒而跡 佛者。余竊異之。高足謙禪。持其狀來 謁。仍請弁其詩文。詩凡五百餘首。文 亦具各體。盡得全鼎之味。儘奇矣。師 俗姓權。法名戒悟。其娠也。母夢月入 懷中。仍以月荷爲號。降胎之夕。天台 山三鳴。山即東海上巨靈也。老於海者 有言曰。此山鳴。鄕有吉事。是夜師果 生焉。咸曰此其徵乎。師性悟才敏。七 歲學書。日誦五六十行。讀數卷。更不 煩師。九流百家。無不涉獵。十一歲祝 髮。受戒於枕虛法師。以傳其衣鉢。其 文也簡古。有作者法。詩亦典雅。無蔬 筍氣。深棲葱嶺。不求塵業。而其與之 遊者。皆一時之選。莫不以昌黎之太顚 陶令之遠公許之。或得其片言隻字。愛 之。若丹山之落羽。滄海之遺珠。亦足以 不朽矣。余性喜浮屠。喜其淸淨不俗也。 而如師者。奚止不俗而已。恨不一識其 面。以追三笑之會。而適任東京。得見 |

| Image with its bounding boxes (reading order of each column is numbered in red) | Annotated Text (punctuation removed) |
| :---- | :---- |
| ![][image5] | 月荷上人遺集序 (Column 1\) 余未見師不知師爲何許人讀其詩 (Column 2\) 觀其志始得其八九分殆是心儒而跡 佛者余竊異之高足謙禪持其狀來 謁仍請弁其詩文詩凡五百餘首文 亦具各體盡得全鼎之味儘奇矣師 俗姓權法名戒悟其娠也母夢月入 懷中仍以月荷爲號降胎之夕天台 山三鳴山即東海上巨靈也老於海者 有言曰此山鳴鄕有吉事是夜師果 生焉咸曰此其徵乎師性悟才敏七 歲學書日誦五六十行讀數卷更不 煩師九流百家無不涉獵十一歲祝 髮受戒於枕虛法師以傳其衣鉢其 文也簡古有作者法詩亦典雅無蔬 筍氣深棲葱嶺不求塵業而其與之 遊者皆一時之選莫不以昌黎之太顚 陶令之遠公許之或得其片言隻字愛 之若丹山之落羽滄海之遺珠亦足以 不朽矣余性喜浮屠喜其淸淨不俗也 而如師者奚止不俗而已恨不一識其 面以追三笑之會而適任東京得見 |