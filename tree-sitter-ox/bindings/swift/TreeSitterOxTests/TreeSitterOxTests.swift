import XCTest
import SwiftTreeSitter
import TreeSitterOx

final class TreeSitterOxTests: XCTestCase {
    func testCanLoadGrammar() throws {
        let parser = Parser()
        let language = Language(language: tree_sitter_ox())
        XCTAssertNoThrow(try parser.setLanguage(language),
                         "Error loading Ox grammar")
    }
}
