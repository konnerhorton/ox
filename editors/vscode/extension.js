const vscode = require("vscode");
const path = require("path");
const fs = require("fs");

let client;

function findLspCommand(workspaceFolders, activeDocument) {
  // Search for .venv/bin/ox-lsp in workspace folders, active file's directory, and their parents
  const searchPaths = [];

  // Add workspace folders
  if (workspaceFolders) {
    for (const folder of workspaceFolders) {
      searchPaths.push(folder.uri.fsPath);
    }
  }

  // Add active document's directory
  if (activeDocument && activeDocument.uri.scheme === "file") {
    searchPaths.push(path.dirname(activeDocument.uri.fsPath));
  }

  // For each starting path, check it and parent directories
  const checkedPaths = new Set();
  for (const startPath of searchPaths) {
    let dir = startPath;
    for (let i = 0; i < 6; i++) {
      if (checkedPaths.has(dir)) break;
      checkedPaths.add(dir);

      const venvPath = path.join(dir, ".venv", "bin", "ox-lsp");
      if (fs.existsSync(venvPath)) {
        return { command: venvPath, cwd: dir };
      }

      const parent = path.dirname(dir);
      if (parent === dir) break;
      dir = parent;
    }
  }

  return null;
}

async function activate(context) {

  // Try to load the language client
  let LanguageClient, TransportKind;
  try {
    const lc = require("vscode-languageclient/node");
    LanguageClient = lc.LanguageClient;
    TransportKind = lc.TransportKind;
  } catch (e) {
    console.log("vscode-languageclient not available, LSP disabled:", e.message);
    return;
  }

  // Find the LSP server
  const activeDoc = vscode.window.activeTextEditor?.document;
  const lspInfo = findLspCommand(vscode.workspace.workspaceFolders, activeDoc);

  if (!lspInfo) {
    // LSP not found - syntax highlighting still works
    return;
  }

  const serverOptions = {
    command: lspInfo.command,
    args: [],
    transport: TransportKind.stdio,
    options: { cwd: lspInfo.cwd },
  };

  const clientOptions = {
    documentSelector: [{ scheme: "file", language: "ox" }],
  };

  client = new LanguageClient(
    "ox",
    "Ox Language Server",
    serverOptions,
    clientOptions
  );

  try {
    await client.start();
  } catch (e) {
    console.error("Ox LSP failed:", e.message);
  }
}

function deactivate() {
  if (client) {
    return client.stop();
  }
}

module.exports = { activate, deactivate };
