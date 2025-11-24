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

	fmt.Println("\nDownloading images from JSON metadata...")

	// Step 2: Download images for all books sequentially
	for i := start; i <= end; i++ {
		bookID := fmt.Sprintf("H%04d", i)
		fmt.Printf("\n[%d/%d] Downloading images for %s...\n", i-start+1, end-start+1, bookID)

		err := DownloadImagesFromJSON(bookID, setting)
		if err != nil {
			fmt.Printf("Error downloading images for %s: %v\n", bookID, err)
		}
	}

	fmt.Println("\nAll books processed!")
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
	// Construct URL
	url := fmt.Sprintf("%s/content/view?dataId=ABC_BJ_%s_T_001&rt=T", setting.Url, bookID)

	// Fetch the page
	resp, err := http.Get(url)
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

	// Extract all image IDs and corresponding text
	var images []ImageInfo
	doc.Find("[data-xsl-kid]").Each(func(i int, s *goquery.Selection) {
		imageID, exists := s.Attr("data-xsl-kid")
		if !exists {
			return
		}

		imageURL := fmt.Sprintf("%s/data/image/ABC_BJ/ABC_BJ_%s/ABC_BJ_%s_%s.jpg", setting.Url, bookID, bookID, imageID)

		// Extract Text
		// The text corresponding to this image/page is in a sibling `dt` element within the same `dl` container.
		// Structure: dl -> span.btns -> button[data-xsl-kid] (Image ID)
		//            dl -> dt.ch (Text)

		// Find the parent dl
		dl := s.Closest("dl")
		text := ""
		clean_text := ""
		if dl.Length() > 0 {
			// Find the text container (dt.ch)
			dt := dl.Find("dt.ch")
			if dt.Length() > 0 {
				// Clone the selection to avoid modifying the original document
				dtClone := dt.Clone()

				// Remove line numbers: span[data-xsl-tag="line"]
				dtClone.Find("span[data-xsl-tag='line']").Remove()

				// Remove footnotes: span[data-xsl-tag="주석"]
				dtClone.Find("span[data-xsl-tag='주석']").Remove()

				text = dtClone.Text()
				// Clean text
				clean_text = CleanText(text)
			} else {
				fmt.Printf("Could not find dt.ch for image %s\n", imageID)
			}
		} else {
			fmt.Printf("Could not find parent dl for image %s\n", imageID)
		}

		images = append(images, ImageInfo{
			ImageID:      imageID,
			ImageURL:     imageURL,
			OriginalText: text,
			CleanText:    clean_text,
			Index:        i,
		})
	})

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
		URL:        url,
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
