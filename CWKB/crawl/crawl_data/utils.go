package crawl_data

import (
	"image"
	"image/jpeg"
	"os"
	"strings"
	"unicode"

	"golang.org/x/image/draw"
)

// ResizeImage resizes the image at the given path so that its largest dimension is 2048 pixels.
// It preserves the aspect ratio.
func ResizeImage(path string) error {
	file, err := os.Open(path)
	if err != nil {
		return err
	}
	img, _, err := image.Decode(file)
	file.Close() // Close immediately after decoding
	if err != nil {
		return err
	}

	bounds := img.Bounds()
	width := bounds.Dx()
	height := bounds.Dy()

	if width <= 2048 && height <= 2048 {
		return nil // No need to resize
	}

	var newWidth, newHeight int
	if width > height {
		newWidth = 2048
		newHeight = (height * 2048) / width
	} else {
		newHeight = 2048
		newWidth = (width * 2048) / height
	}

	dst := image.NewRGBA(image.Rect(0, 0, newWidth, newHeight))
	draw.CatmullRom.Scale(dst, dst.Bounds(), img, bounds, draw.Over, nil)

	outFile, err := os.Create(path)
	if err != nil {
		return err
	}
	defer outFile.Close()

	return jpeg.Encode(outFile, dst, nil)
}

// CleanText removes punctuation and whitespaces from the text.
// It keeps only letters and numbers (and maybe some specific chars if needed, but guidelines say "remove punctuation and whitespaces").
// Based on guidelines: "remove punctuation and whitespaces from the text for recognition dataset".
// This usually means keeping CJK characters and removing everything else that is not a character.
func CleanText(text string) string {
	var builder strings.Builder
	lastWasNewline := false
	for _, r := range text {
		if r == '\n' || r == '\r' {
			if !lastWasNewline {
				builder.WriteRune('\n')
				lastWasNewline = true
			}
		} else if !unicode.IsPunct(r) && !unicode.IsSpace(r) && !unicode.IsSymbol(r) {
			builder.WriteRune(r)
			lastWasNewline = false
		}
	}
	return builder.String()
}
