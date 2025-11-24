package main

import (
	"fmt"
	"nlp-chineseocr/crawl_data"
)

func main() {
	fmt.Println("MAIN GOLANG PROGRAM, created by cieldt")
	// Crawl Data
	// setting := crawl_data.Setting{
	// 	DataFolder: "E:\\data_nlp_test",
	// 	Url:        "https://kabc.dongguk.edu",
	// }
	// crawl_data.GetMetadataOfBook("H0030", setting)

	crawl_data.Crawl_NLP_Data()
}
