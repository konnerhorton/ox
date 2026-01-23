package tree_sitter_ox_test

import (
	"testing"

	tree_sitter "github.com/tree-sitter/go-tree-sitter"
	tree_sitter_ox "github.com/tree-sitter/tree-sitter-ox/bindings/go"
)

func TestCanLoadGrammar(t *testing.T) {
	language := tree_sitter.NewLanguage(tree_sitter_ox.Language())
	if language == nil {
		t.Errorf("Error loading ox grammar")
	}
}
