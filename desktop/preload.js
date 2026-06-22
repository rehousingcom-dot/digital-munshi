// Preload — abhi minimal. Future mein native features (printer, file save,
// barcode scanner) yahan se web app ko expose kar sakte hain.
const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("digitalMunshi", {
  platform: process.platform,
  isDesktop: true,
});
