# Simplii Chrome Extension

A simple Chrome extension to send any webpage URL directly to your Simplii dashboard for processing.

## Installation

1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode" (top right toggle)
3. Click "Load unpacked"
4. Select the `chrome_extension` folder from your Simplii project

## Usage

1. **Get your API token:**
   - Open Simplii web app and log in
   - Click "Settings" in the sidebar
   - Click "Generate" next to "Chrome Extension Token"
   - Click "Copy" to copy the token

2. **Use the extension:**
   - Navigate to any webpage
   - Click the Simplii extension icon in Chrome toolbar
   - Paste your API token in the token field
   - Click "Send to Simplii"

3. **Process the URL:**
   - The URL appears immediately in your Simplii queue
   - The existing workflow processes it automatically
   - Check your queue panel to see the progress

## Requirements

- Simplii backend running on `http://localhost:8000`
- Valid API token from Simplii settings
- Chrome browser

## Features

- Automatically detects current page URL
- Simple token-based authentication
- Loading states and error handling
- Clean, minimal UI matching Simplii design