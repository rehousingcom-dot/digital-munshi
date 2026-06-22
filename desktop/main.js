// Digital Munshi ERP — Electron desktop wrapper.
// Humari web app ko ek native desktop app (Mac/Windows/Linux) mein chalata hai.
// Server URL: default local (127.0.0.1:8000). Cloud pe deploy ke baad DM_SERVER_URL set karein.
const { app, BrowserWindow, Menu, shell } = require("electron");
const path = require("path");

const SERVER_URL = process.env.DM_SERVER_URL || "http://127.0.0.1:8000/";

let mainWindow = null;
let waWindow = null;

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1320, height: 860, minWidth: 1000, minHeight: 620,
    title: "Digital Munshi",
    backgroundColor: "#1e1b4b",
    webPreferences: { contextIsolation: true, preload: path.join(__dirname, "preload.js") },
  });

  mainWindow.loadURL(SERVER_URL);

  // Server na chale to friendly offline page
  mainWindow.webContents.on("did-fail-load", (e, code, desc, url) => {
    if (url && url.startsWith(SERVER_URL)) {
      mainWindow.loadFile(path.join(__dirname, "offline.html"));
    }
  });

  // Same-server links app ke andar; external (wa.me etc.) default browser mein
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith(SERVER_URL)) return { action: "allow" };
    shell.openExternal(url);
    return { action: "deny" };
  });

  mainWindow.on("closed", () => { mainWindow = null; });
}

// WhatsApp Web ko ek alag window mein — yahan QR scan karke documents bhej sakte hain
function openWhatsAppWeb() {
  if (waWindow) { waWindow.focus(); return; }
  waWindow = new BrowserWindow({
    width: 1100, height: 780, title: "WhatsApp Web — Digital Munshi",
    webPreferences: { partition: "persist:whatsapp" }, // session yaad rahe
  });
  waWindow.loadURL("https://web.whatsapp.com");
  waWindow.on("closed", () => { waWindow = null; });
}

function buildMenu() {
  const isMac = process.platform === "darwin";
  const template = [
    ...(isMac ? [{ label: "Digital Munshi", submenu: [{ role: "about" }, { type: "separator" }, { role: "quit" }] }] : []),
    { label: "File", submenu: [isMac ? { role: "close" } : { role: "quit" }] },
    { label: "View", submenu: [
      { role: "reload" }, { role: "forceReload" }, { role: "toggleDevTools" },
      { type: "separator" }, { role: "resetZoom" }, { role: "zoomIn" }, { role: "zoomOut" },
      { type: "separator" }, { role: "togglefullscreen" },
    ]},
    { label: "WhatsApp", submenu: [
      { label: "Open WhatsApp Web (QR scan)", click: openWhatsAppWeb },
    ]},
    { label: "Window", submenu: [{ role: "minimize" }, { role: "zoom" }, ...(isMac ? [{ role: "front" }] : [{ role: "close" }])] },
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (mainWindow) { if (mainWindow.isMinimized()) mainWindow.restore(); mainWindow.focus(); }
  });
  app.whenReady().then(() => {
    buildMenu();
    createMainWindow();
    app.on("activate", () => { if (BrowserWindow.getAllWindows().length === 0) createMainWindow(); });
  });
  app.on("window-all-closed", () => { if (process.platform !== "darwin") app.quit(); });
}
