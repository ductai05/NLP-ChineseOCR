package crawl_data

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/PuerkitoBio/goquery"
)

type Setting struct {
	DataFolder string
	Url        string
}

func Crawl_NLP_Data() {
	setting := Setting{
		DataFolder: ".\\data_nlp",
		Url:        "https://kabc.dongguk.edu",
	}

	fmt.Printf("Crawl data from \"%s\"\n", setting.Url)
	fmt.Printf("Save data to \"%s\"\n", setting.DataFolder)

	// Range H0029 - H0040
	start := 29
	end := 40

	fmt.Println("\nExporting image metadata to JSON...")

	// Step 1: Export image info for all books sequentially
	for i := start; i <= end; i++ {
		bookID := fmt.Sprintf("H%04d", i)
		fmt.Printf("\n[%d/%d] Exporting metadata for %s...\n", i-start+1, end-start+1, bookID)

		err := GetMetadataOfBook(bookID, setting)
		if err != nil {
			fmt.Printf("Error exporting %s: %v\n", bookID, err)
		}

		// Be nice to the server
		time.Sleep(1 * time.Second)
	}

	// fmt.Println("\nDownloading images from JSON metadata...")

	// // Step 2: Download images for all books sequentially
	// for i := start; i <= end; i++ {
	// 	bookID := fmt.Sprintf("H%04d", i)
	// 	fmt.Printf("\n[%d/%d] Downloading images for %s...\n", i-start+1, end-start+1, bookID)

	// 	err := DownloadImagesFromJSON(bookID, setting)
	// 	if err != nil {
	// 		fmt.Printf("Error downloading images for %s: %v\n", bookID, err)
	// 	}
	// }

	// fmt.Println("\nAll books processed!")
}

// DownloadImagesFromJSON reads the JSON metadata file and downloads all images for a book
func DownloadImagesFromJSON(bookID string, setting Setting) error {
	fmt.Printf("Downloading images from JSON for book: %s\n", bookID)

	// First, we need to find the correct folder by searching for folders matching the pattern *_<bookID>
	// or we can read available JSON files to find the book name
	var jsonPath string
	var folderName string

	// Search for folders matching pattern *_<bookID>
	entries, err := os.ReadDir(setting.DataFolder)
	if err != nil {
		return fmt.Errorf("failed to read data folder: %w", err)
	}

	for _, entry := range entries {
		if entry.IsDir() && strings.HasSuffix(entry.Name(), "_"+bookID) {
			folderName = entry.Name()
			jsonPath = filepath.Join(setting.DataFolder, folderName, fmt.Sprintf("%s_images.json", bookID))
			break
		}
	}

	if jsonPath == "" {
		return fmt.Errorf("could not find folder for book: %s. Please run GetMetadataOfBook first", bookID)
	}

	// Check if JSON file exists
	if _, err := os.Stat(jsonPath); os.IsNotExist(err) {
		return fmt.Errorf("metadata JSON not found: %s. Please run ExportBookImageInfo first", jsonPath)
	}

	// Read JSON file
	data, err := os.ReadFile(jsonPath)
	if err != nil {
		return fmt.Errorf("failed to read JSON: %w", err)
	}

	// Parse JSON
	var metadata BookImageMetadata
	err = json.Unmarshal(data, &metadata)
	if err != nil {
		return fmt.Errorf("failed to parse JSON: %w", err)
	}

	fmt.Printf("Found %d images in metadata\n", len(metadata.Images))

	// Create images directory using the folder with bookName_bookID format
	imagesDir := filepath.Join(setting.DataFolder, folderName, "images")
	if err := os.MkdirAll(imagesDir, 0755); err != nil {
		return fmt.Errorf("failed to create images directory: %w", err)
	}

	// Download each image concurrently using goroutines
	successCount := 0
	skippedCount := 0
	failedCount := 0

	// Create a mutex to protect the counters
	var mu sync.Mutex

	// Create a WaitGroup to wait for all goroutines to complete
	var wg sync.WaitGroup

	// Create a channel to limit concurrent downloads (worker pool pattern)
	maxConcurrentDownloads := 5
	semaphore := make(chan struct{}, maxConcurrentDownloads)

	for i, imgInfo := range metadata.Images {
		// Add to WaitGroup
		wg.Add(1)

		// Launch goroutine for each image
		go func(index int, info ImageInfo) {
			defer wg.Done()

			// Acquire semaphore (limit concurrent downloads)
			semaphore <- struct{}{}
			defer func() { <-semaphore }() // Release semaphore

			imagePath := filepath.Join(imagesDir, fmt.Sprintf("%s_%s.jpg", bookID, info.ImageID))

			// Check if image already exists
			if _, err := os.Stat(imagePath); err == nil {
				mu.Lock()
				skippedCount++
				fmt.Printf("[%d/%d] Skipped %s (already exists)\n", index+1, len(metadata.Images), info.ImageID)
				mu.Unlock()
				return
			}

			mu.Lock()
			fmt.Printf("[%d/%d] Downloading %s...\n", index+1, len(metadata.Images), info.ImageID)
			mu.Unlock()

			// Download image
			err := downloadFile(info.ImageURL, imagePath)
			if err != nil {
				mu.Lock()
				fmt.Printf("    Failed: %v\n", err)
				failedCount++
				mu.Unlock()
				return
			}

			// Resize image
			err = ResizeImage(imagePath)
			if err != nil {
				mu.Lock()
				fmt.Printf("Downloaded but failed to resize: %v\n", err)
				mu.Unlock()
			} else {
				mu.Lock()
				fmt.Printf("Success %s\n", info.ImageID)
				mu.Unlock()
			}

			mu.Lock()
			successCount++
			mu.Unlock()

			// Be nice to the server
			time.Sleep(250 * time.Millisecond)
		}(i, imgInfo)
	}

	// Wait for all goroutines to complete
	wg.Wait()

	fmt.Printf("\nSummary: %d downloaded, %d skipped, %d failed\n", successCount, skippedCount, failedCount)
	return nil
}

func downloadFile(url string, filepath string) error {
	resp, err := http.Get(url)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return fmt.Errorf("status code %d", resp.StatusCode)
	}

	out, err := os.Create(filepath)
	if err != nil {
		return err
	}
	defer out.Close()

	_, err = io.Copy(out, resp.Body)
	return err
}

// fetchTextFromViewer fetches the text content from the viewer page for a specific image
// URL format: https://kabc.dongguk.edu/viewer/view?dataId=ABC_BJ_{bookID}_T_001&imgId={imageID}
func fetchTextFromViewer(bookID string, imageID string, setting Setting) (originalText string, cleanText string, err error) {
	viewerURL := fmt.Sprintf("%s/viewer/view?dataId=ABC_BJ_%s_T_001&imgId=%s", setting.Url, bookID, imageID)

	resp, err := http.Get(viewerURL)
	if err != nil {
		return "", "", err
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return "", "", fmt.Errorf("status code error: %d %s", resp.StatusCode, resp.Status)
	}

	doc, err := goquery.NewDocumentFromReader(resp.Body)
	if err != nil {
		return "", "", err
	}

	// Find the text container: div[data-xsl-kid="{imageID}"]
	// The text is in .xsl_body div[data-xsl-kid]
	selector := fmt.Sprintf("div[data-xsl-kid='%s']", imageID)
	textContainer := doc.Find(selector).First()

	if textContainer.Length() == 0 {
		return "", "", fmt.Errorf("could not find text container for image %s", imageID)
	}

	// Clone to avoid modifying original
	textClone := textContainer.Clone()

	// Remove line numbers: span[data-xsl-tag="line"]
	textClone.Find("span[data-xsl-tag='line']").Remove()

	// Remove footnote markers: span[data-xsl-tag="주석"] (e.g., 1), 2), 3))
	textClone.Find("span[data-xsl-tag='주석']").Remove()

	// Remove footnote content: span[data-xsl-tag="각주"]
	textClone.Find("span[data-xsl-tag='각주']").Remove()

	// Remove hidden footnote references
	textClone.Find(".desc-jusok-ref").Remove()

	// Remove footnote references at the end: .desc-jusok-ref-bj
	textClone.Find(".desc-jusok-ref-bj").Remove()

	// Remove indent spans
	textClone.Find("span[data-indent]").Remove()

	// Get text
	originalText = textClone.Text()

	// Clean text
	cleanText = CleanText(originalText)

	return originalText, cleanText, nil
}

// ====================== EXPORT BOOK AND IMAGE METADATA ======================

// ImageInfo represents information about a single image/page
type ImageInfo struct {
	ImageID      string `json:"image_id"`
	ImageURL     string `json:"image_url"`
	OriginalText string `json:"original_text"`
	CleanText    string `json:"clean_text"`
	Index        int    `json:"index"`
}

// BookImageMetadata represents all images metadata for a book
type BookImageMetadata struct {
	BookID     string      `json:"book_id"`
	BookName   string      `json:"book_name"`
	URL        string      `json:"url"`
	TotalPages int         `json:"total_pages"`
	Images     []ImageInfo `json:"images"`
}

// GetMetadataOfBook fetches a book page, extracts all image IDs (data-xsl-kid),
// and saves the information to a JSON file
func GetMetadataOfBook(bookID string, setting Setting) error {
	// Construct URL for the main content page to get list of image IDs
	contentURL := fmt.Sprintf("%s/content/view?dataId=ABC_BJ_%s_T_001&rt=T", setting.Url, bookID)

	// Fetch the page
	resp, err := http.Get(contentURL)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return fmt.Errorf("status code error: %d %s", resp.StatusCode, resp.Status)
	}

	// Load the HTML document
	doc, err := goquery.NewDocumentFromReader(resp.Body)
	if err != nil {
		return err
	}

	// First, collect all image IDs from the content page
	var imageIDs []string
	doc.Find("[data-xsl-kid]").Each(func(i int, s *goquery.Selection) {
		imageID, exists := s.Attr("data-xsl-kid")
		if exists {
			imageIDs = append(imageIDs, imageID)
		}
	})

	fmt.Printf("Found %d image IDs\n", len(imageIDs))

	// Extract all image IDs and corresponding text from viewer pages
	var images []ImageInfo
	for i, imageID := range imageIDs {
		fmt.Printf("[%d/%d] Fetching text for %s...\n", i+1, len(imageIDs), imageID)

		imageURL := fmt.Sprintf("%s/data/image/ABC_BJ/ABC_BJ_%s/ABC_BJ_%s_%s.jpg", setting.Url, bookID, bookID, imageID)

		// Fetch text from the viewer page
		text, cleanText, err := fetchTextFromViewer(bookID, imageID, setting)
		if err != nil {
			fmt.Printf("Warning: failed to fetch text for %s: %v\n", imageID, err)
		}

		images = append(images, ImageInfo{
			ImageID:      imageID,
			ImageURL:     imageURL,
			OriginalText: text,
			CleanText:    cleanText,
			Index:        i,
		})

		// Be nice to the server
		time.Sleep(500 * time.Millisecond)
	}

	// Extract book name from the first line of images[0].CleanText
	bookName := ""
	if len(images) > 0 {
		lines := strings.Split(strings.TrimSpace(images[0].CleanText), "\n")
		if len(lines) > 0 {
			bookName = strings.TrimSpace(lines[0])
		}
	}

	fmt.Printf("Extracted Book Name: %s\n", bookName)

	// Create metadata
	metadata := BookImageMetadata{
		BookID:     bookID,
		BookName:   bookName,
		URL:        contentURL,
		TotalPages: len(images),
		Images:     images,
	}

	// Create output directory with format: <BookName>_<H00xx>
	folderName := fmt.Sprintf("%s_%s", bookName, bookID)
	bookDir := filepath.Join(setting.DataFolder, folderName)
	if err := os.MkdirAll(bookDir, 0755); err != nil {
		return err
	}

	// Save to JSON file
	jsonPath := filepath.Join(bookDir, fmt.Sprintf("%s_images.json", bookID))

	// Create file
	file, err := os.Create(jsonPath)
	if err != nil {
		return err
	}
	defer file.Close()

	// Create encoder with HTML escaping disabled
	encoder := json.NewEncoder(file)
	encoder.SetEscapeHTML(false)
	encoder.SetIndent("", "  ")

	// Encode to file
	err = encoder.Encode(metadata)
	if err != nil {
		return err
	}

	fmt.Printf("✓ Exported %d images info for %s to %s\n", len(images), bookID, jsonPath)

	// Create puncs folder for original text files
	puncsDir := filepath.Join(bookDir, "puncs")
	if err := os.MkdirAll(puncsDir, 0755); err != nil {
		return fmt.Errorf("failed to create puncs directory: %w", err)
	}

	// Save original text for each image to separate txt files
	for _, imgInfo := range images {
		txtFilename := fmt.Sprintf("%s_%s.txt", bookID, imgInfo.ImageID)
		txtPath := filepath.Join(puncsDir, txtFilename)

		// Write original text to file
		err := os.WriteFile(txtPath, []byte(imgInfo.OriginalText), 0644)
		if err != nil {
			fmt.Printf("Warning: failed to write %s: %v\n", txtFilename, err)
			continue
		}
	}

	fmt.Printf("✓ Saved %d original text files to puncs folder\n", len(images))
	return nil
}
