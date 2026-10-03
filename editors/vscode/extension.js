const vscode = require("vscode");
const path = require("path");
const fs = require("fs");
const os = require("os");

const INSTALL_COMMAND = "uv tool install git+https://github.com/konnerhorton/ox";
const DOCS_URL = "https://konnerhorton.github.io/ox/editor-support/";
const MISSING_WARNING_KEY = "ox.lspMissingWarningDismissed";

const isWindows = process.platform === "win32";
const VENV_BIN = isWindows ? path.join(".venv", "Scripts") : path.join(".venv", "bin");
const EXE_NAMES = isWindows ? ["ox-lsp.exe", "ox-lsp.cmd", "ox-lsp"] : ["ox-lsp"];

let client;
let LanguageClient, TransportKind;

function isExecutable(file) {
  try {
    fs.accessSync(file, isWindows ? fs.constants.F_OK : fs.constants.X_OK);
    return fs.statSync(file).isFile();
  } catch {
    return false;
  }
}

function findInVenv(workspaceFolders, activeDocument) {
  // Search for .venv/{bin,Scripts}/ox-lsp in workspace folders, the active file's directory, and their parents
  const searchPaths = [];

  if (workspaceFolders) {
    for (const folder of workspaceFolders) {
      searchPaths.push(folder.uri.fsPath);
    }
  }

  if (activeDocument && activeDocument.uri.scheme === "file") {
    searchPaths.push(path.dirname(activeDocument.uri.fsPath));
  }

  const checkedPaths = new Set();
  for (const startPath of searchPaths) {
    let dir = startPath;
    for (let i = 0; i < 6; i++) {
      if (checkedPaths.has(dir)) break;
      checkedPaths.add(dir);

      for (const exe of EXE_NAMES) {
        const candidate = path.join(dir, VENV_BIN, exe);
        if (isExecutable(candidate)) {
          return { command: candidate, cwd: dir };
        }
      }

      const parent = path.dirname(dir);
      if (parent === dir) break;
      dir = parent;
    }
  }

  return null;
}

function findOnPath() {
  const dirs = (process.env.PATH || "").split(path.delimiter).filter(Boolean);
  for (const dir of dirs) {
    for (const exe of EXE_NAMES) {
      const candidate = path.join(dir, exe);
      if (isExecutable(candidate)) {
        return { command: candidate, cwd: undefined };
      }
    }
  }
  return null;
}

function expandHome(p) {
  if (p === "~" || p.startsWith("~/") || p.startsWith("~\\")) {
    return path.join(os.homedir(), p.slice(1));
  }
  return p;
}

function findLspCommand() {
  // Resolution order: ox.lsp.path setting → project .venv → PATH
  const configured = vscode.workspace.getConfiguration("ox").get("lsp.path", "").trim();
  if (configured) {
    const command = expandHome(configured);
    if (isExecutable(command)) {
      return { command, cwd: undefined };
    }
    vscode.window.showErrorMessage(
      `Ox: ox.lsp.path is set to "${configured}", but no executable was found there.`
    );
    return null;
  }

  const activeDoc = vscode.window.activeTextEditor?.document;
  return findInVenv(vscode.workspace.workspaceFolders, activeDoc) || findOnPath();
}

async function warnMissing(context) {
  if (context.globalState.get(MISSING_WARNING_KEY)) return;

  const choice = await vscode.window.showWarningMessage(
    "Ox: ox-lsp was not found, so diagnostics and completions are disabled " +
      `(syntax highlighting still works). Install it with \`${INSTALL_COMMAND}\`, ` +
      "or set ox.lsp.path.",
    "Copy Install Command",
    "Open Docs",
    "Don't Show Again"
  );

  if (choice === "Copy Install Command") {
    await vscode.env.clipboard.writeText(INSTALL_COMMAND);
  } else if (choice === "Open Docs") {
    vscode.env.openExternal(vscode.Uri.parse(DOCS_URL));
  } else if (choice === "Don't Show Again") {
    await context.globalState.update(MISSING_WARNING_KEY, true);
  }
}

async function startClient(context) {
  const lspInfo = findLspCommand();
  if (!lspInfo) {
    if (!vscode.workspace.getConfiguration("ox").get("lsp.path", "").trim()) {
      warnMissing(context);
    }
    return;
  }

  const serverOptions = {
    command: lspInfo.command,
    args: [],
    transport: TransportKind.stdio,
    options: lspInfo.cwd ? { cwd: lspInfo.cwd } : {},
  };

  const clientOptions = {
    documentSelector: [{ scheme: "file", language: "ox" }],
  };

  client = new LanguageClient("ox", "Ox Language Server", serverOptions, clientOptions);

  try {
    await client.start();
  } catch (e) {
    client = undefined;
    vscode.window.showErrorMessage(`Ox: language server failed to start: ${e.message}`);
  }
}

async function stopClient() {
  if (client) {
    const c = client;
    client = undefined;
    await c.stop();
  }
}

async function restartClient(context) {
  await stopClient();
  await startClient(context);
}

async function activate(context) {
  // Try to load the language client
  try {
    const lc = require("vscode-languageclient/node");
    LanguageClient = lc.LanguageClient;
    TransportKind = lc.TransportKind;
  } catch (e) {
    console.log("vscode-languageclient not available, LSP disabled:", e.message);
    return;
  }

  context.subscriptions.push(
    vscode.commands.registerCommand("ox.restartLsp", () => restartClient(context)),
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration("ox.lsp.path")) {
        restartClient(context);
      }
    })
  );

  await startClient(context);
}

function deactivate() {
  return stopClient();
}

module.exports = { activate, deactivate };
